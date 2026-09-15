import json
import os
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timedelta

try:
    import fcntl
except ImportError:  # pragma: no cover - o player usa recursos Unix/WSL
    fcntl = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_STATS = os.path.join(BASE_DIR, "stats.json")
VERSAO = 1
INTERVALO_SALVAMENTO = 5.0
LIMITE_REPRODUCAO_SEGUNDOS = 4 * 60
LIMITE_SEM_DURACAO_SEGUNDOS = 30


class ErroEstatisticas(Exception):
    pass


def _agora_local():
    return datetime.now().astimezone()


def _iso(instante):
    return instante.isoformat(timespec="seconds")


def _dados_vazios():
    return {"version": VERSAO, "sessions": []}


def _validar_dados(dados):
    if not isinstance(dados, dict) or not isinstance(
        dados.get("sessions"), list
    ):
        raise ErroEstatisticas("formato inválido")
    return dados


@contextmanager
def _bloquear(caminho):
    arquivo = open(f"{caminho}.lock", "a+", encoding="utf-8")
    try:
        if fcntl is not None:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)
        arquivo.close()


def carregar(caminho=CAMINHO_STATS):
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return _validar_dados(json.load(arquivo))
    except FileNotFoundError:
        return _dados_vazios()
    except (OSError, json.JSONDecodeError, ErroEstatisticas) as erro:
        raise ErroEstatisticas(
            f"não foi possível ler '{caminho}': {erro}"
        ) from erro


def _salvar_atomico(dados, caminho):
    diretorio = os.path.dirname(os.path.abspath(caminho))
    os.makedirs(diretorio, exist_ok=True)
    temporario = None
    try:
        temporario = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".stats-",
            suffix=".tmp",
            dir=diretorio,
            delete=False,
        )
        json.dump(dados, temporario, ensure_ascii=False, indent=2)
        temporario.write("\n")
        temporario.flush()
        os.fsync(temporario.fileno())
        temporario.close()
        os.replace(temporario.name, caminho)
        temporario = None
    except OSError as erro:
        raise ErroEstatisticas(
            f"não foi possível salvar '{caminho}': {erro}"
        ) from erro
    finally:
        if temporario is not None:
            try:
                nome = temporario.name
                if not temporario.closed:
                    temporario.close()
                os.unlink(nome)
            except OSError:
                pass


def salvar_sessao(sessao, caminho=CAMINHO_STATS):
    """Insere ou atualiza uma sessão sem perder gravações de outro processo."""
    try:
        with _bloquear(caminho):
            dados = carregar(caminho)
            for indice, existente in enumerate(dados["sessions"]):
                if existente.get("id") == sessao["id"]:
                    dados["sessions"][indice] = sessao
                    break
            else:
                dados["sessions"].append(sessao)
            _salvar_atomico(dados, caminho)
    except OSError as erro:
        raise ErroEstatisticas(
            f"não foi possível bloquear '{caminho}': {erro}"
        ) from erro


def caminho_musica(musica):
    normalizado = os.path.normpath(str(musica)).replace(os.sep, "/")
    while normalizado.startswith("./"):
        normalizado = normalizado[2:]
    if normalizado == "music" or normalizado.startswith("music/"):
        return normalizado
    return f"music/{normalizado}"


def pasta_musica(musica):
    relativo = caminho_musica(musica).removeprefix("music/")
    pasta = os.path.dirname(relativo).replace(os.sep, "/")
    return f"{pasta}/" if pasta else "music/"


def limite_reproducao(duracao):
    if duracao is None or duracao <= 0:
        return LIMITE_SEM_DURACAO_SEGUNDOS
    return min(LIMITE_REPRODUCAO_SEGUNDOS, duracao * 0.5)


class RastreadorReproducao:
    def __init__(self, caminho=CAMINHO_STATS):
        self.caminho = caminho
        self.sessao = None
        self.ultima_posicao = None
        self.ultimo_monotonic = None
        self.ultima_pausa = True
        self.ultimo_salvamento = None
        self.desativado = False
        self._erro_exibido = False

    def _nova_sessao(self, musica, duracao, agora):
        musica = caminho_musica(musica)
        self.sessao = {
            "id": uuid.uuid4().hex,
            "track": musica,
            "folder": pasta_musica(musica),
            "started_at": _iso(agora),
            "ended_at": _iso(agora),
            "duration_seconds": (
                round(float(duracao), 3) if duracao is not None else None
            ),
            "listened_seconds": 0.0,
            "listened_by_day": {},
            "counted_play": False,
            "counted_at": None,
        }

    def _registrar_tempo(self, segundos, agora):
        if self.sessao is None or segundos <= 0:
            return
        segundos = float(segundos)
        self.sessao["listened_seconds"] += segundos
        dia = agora.date().isoformat()
        por_dia = self.sessao["listened_by_day"]
        por_dia[dia] = por_dia.get(dia, 0.0) + segundos
        self.sessao["ended_at"] = _iso(agora)
        if (
            not self.sessao["counted_play"]
            and self.sessao["listened_seconds"]
            >= limite_reproducao(self.sessao.get("duration_seconds"))
        ):
            self.sessao["counted_play"] = True
            self.sessao["counted_at"] = _iso(agora)

    def _salvar(self):
        if self.sessao is None or self.desativado:
            return
        sessao = dict(self.sessao)
        sessao["listened_seconds"] = round(sessao["listened_seconds"], 3)
        sessao["listened_by_day"] = {
            dia: round(segundos, 3)
            for dia, segundos in sessao["listened_by_day"].items()
        }
        try:
            salvar_sessao(sessao, self.caminho)
        except ErroEstatisticas as erro:
            self.desativado = True
            if not self._erro_exibido:
                print(f"Aviso: estatísticas desativadas: {erro}", file=sys.stderr)
                self._erro_exibido = True

    def _finalizar_sessao(self, agora):
        if self.sessao is None:
            return
        self.sessao["ended_at"] = _iso(agora)
        if self.sessao["listened_seconds"] > 0:
            self._salvar()
        self.sessao = None

    def atualizar(
        self,
        musica,
        posicao,
        duracao,
        pausada,
        *,
        instante_monotonic=None,
        agora=None,
    ):
        if musica is None or posicao is None:
            return
        agora = agora or _agora_local()
        instante_monotonic = (
            time.monotonic()
            if instante_monotonic is None
            else instante_monotonic
        )
        musica = caminho_musica(musica)
        posicao = float(posicao)
        pausada = bool(pausada)

        mudou_musica = (
            self.sessao is not None and self.sessao["track"] != musica
        )
        reiniciou = (
            self.sessao is not None
            and not mudou_musica
            and self.ultima_posicao is not None
            and posicao < self.ultima_posicao - 1.0
        )
        if mudou_musica or reiniciou:
            self._finalizar_sessao(agora)
            self.ultima_posicao = None
            self.ultimo_monotonic = None

        if self.sessao is None:
            self._nova_sessao(musica, duracao, agora)
        elif duracao is not None and duracao > 0:
            self.sessao["duration_seconds"] = round(float(duracao), 3)

        if self.ultima_posicao is not None and self.ultimo_monotonic is not None:
            avancou = posicao - self.ultima_posicao
            passou = max(0.0, instante_monotonic - self.ultimo_monotonic)
            # Limitar pelo relógio evita contar saltos feitos pelo usuário.
            if avancou > 0 and not self.ultima_pausa:
                self._registrar_tempo(min(avancou, passou + 0.25), agora)

        self.ultima_posicao = posicao
        self.ultimo_monotonic = instante_monotonic
        self.ultima_pausa = pausada

        if (
            self.ultimo_salvamento is None
            or instante_monotonic - self.ultimo_salvamento
            >= INTERVALO_SALVAMENTO
        ):
            if self.sessao["listened_seconds"] > 0:
                self._salvar()
            self.ultimo_salvamento = instante_monotonic

    def finalizar(self, *, agora=None):
        self._finalizar_sessao(agora or _agora_local())


PERIODOS = {
    "today": "HOJE",
    "week": "ESTA SEMANA",
    "month": "ESTE MÊS",
    "year": "ESTE ANO",
    "all": "ALL TIME",
    "all-time": "ALL TIME",
}


def inicio_periodo(periodo, hoje=None):
    hoje = hoje or date.today()
    if periodo == "today":
        return hoje
    if periodo == "week":
        return hoje - timedelta(days=hoje.weekday())
    if periodo == "month":
        return hoje.replace(day=1)
    if periodo == "year":
        return hoje.replace(month=1, day=1)
    if periodo in ("all", "all-time"):
        return None
    raise ValueError(f"período desconhecido: {periodo}")


def _data_iso(valor):
    try:
        return datetime.fromisoformat(valor).date()
    except (TypeError, ValueError):
        return None


def calcular(dados, periodo, hoje=None):
    hoje = hoje or date.today()
    inicio = inicio_periodo(periodo, hoje)
    tempo_por_musica = defaultdict(float)
    reproducoes = Counter()
    reproducoes_pasta = Counter()
    tempo_total = 0.0

    def dentro(data_registro):
        return data_registro is not None and data_registro <= hoje and (
            inicio is None or data_registro >= inicio
        )

    for sessao in dados.get("sessions", []):
        musica = sessao.get("track")
        if not musica:
            continue
        for dia, segundos in sessao.get("listened_by_day", {}).items():
            data_registro = _data_iso(dia)
            if dentro(data_registro):
                try:
                    segundos = max(0.0, float(segundos))
                except (TypeError, ValueError):
                    continue
                tempo_total += segundos
                tempo_por_musica[musica] += segundos

        if sessao.get("counted_play") and dentro(
            _data_iso(sessao.get("counted_at"))
        ):
            reproducoes[musica] += 1
            reproducoes_pasta[
                sessao.get("folder") or pasta_musica(musica)
            ] += 1

    return {
        "listened_seconds": tempo_total,
        "plays": sum(reproducoes.values()),
        "different_tracks": len(tempo_por_musica),
        "track_plays": reproducoes,
        "folder_plays": reproducoes_pasta,
    }


def formatar_duracao(segundos):
    total = max(0, int(round(segundos)))
    horas, resto = divmod(total, 3600)
    minutos, segundos = divmod(resto, 60)
    partes = []
    if horas:
        partes.append(f"{horas}h")
    if minutos:
        partes.append(f"{minutos}min")
    if not partes:
        partes.append(f"{segundos}s")
    return " ".join(partes)


def _nomes_exibicao(musicas):
    contagem = Counter(os.path.basename(musica) for musica in musicas)
    return {
        musica: (
            os.path.basename(musica)
            if contagem[os.path.basename(musica)] == 1
            else musica.removeprefix("music/")
        )
        for musica in musicas
    }


def _linhas_ranking(resultado, limite=10):
    ranking = resultado["track_plays"].most_common(limite)
    if not ranking:
        return ["Nenhuma reprodução contabilizada."]
    nomes = _nomes_exibicao(resultado["track_plays"])
    largura = max(len(nomes[musica]) for musica, _ in ranking)
    return [
        f"{indice}. {nomes[musica]:<{largura}}  {total}x"
        for indice, (musica, total) in enumerate(ranking, 1)
    ]


def _pasta_mais_ouvida(resultado):
    if not resultado["folder_plays"]:
        return "Nenhuma reprodução contabilizada."
    pasta, total = resultado["folder_plays"].most_common(1)[0]
    unidade = "reprodução" if total == 1 else "reproduções"
    return f"{pasta} — {total} {unidade}"


def exibir_periodo(dados, periodo, hoje=None):
    resultado = calcular(dados, periodo, hoje)
    print(f"=== ESTATÍSTICAS — {PERIODOS[periodo]} ===\n")
    print(f"Tempo ouvindo: {formatar_duracao(resultado['listened_seconds'])}")
    print(f"Músicas reproduzidas: {resultado['plays']}")
    print(f"Músicas diferentes: {resultado['different_tracks']}\n")
    print("Mais tocadas:\n")
    print("\n".join(_linhas_ranking(resultado)))
    print("\nPasta mais ouvida:")
    print(_pasta_mais_ouvida(resultado))


def exibir_resumo(dados, hoje=None):
    hoje = hoje or date.today()
    geral = calcular(dados, "all", hoje)
    print("=== ESTATÍSTICAS ===\n")
    print("ALL TIME\n")
    print(
        f"Tempo total ouvindo: {formatar_duracao(geral['listened_seconds'])}"
    )
    print(f"Músicas reproduzidas: {geral['plays']}")
    print(f"Músicas diferentes: {geral['different_tracks']}\n")
    print("Mais tocadas:")
    print("\n".join(_linhas_ranking(geral, limite=5)))

    for periodo, titulo in (
        ("today", "Hoje"),
        ("week", "Esta semana"),
        ("month", "Este mês"),
        ("year", "Este ano"),
    ):
        resultado = calcular(dados, periodo, hoje)
        print(f"\n{titulo}:")
        print(
            f"Tempo ouvindo: {formatar_duracao(resultado['listened_seconds'])}"
        )
        print(f"Músicas: {resultado['plays']}")

    print("\nPasta mais ouvida:")
    print(_pasta_mais_ouvida(geral))


def executar(periodo=None, caminho=CAMINHO_STATS):
    if periodo is not None and periodo not in PERIODOS:
        print(
            "Uso: player stats [today|week|month|year|all|all-time]",
            file=sys.stderr,
        )
        return 2
    try:
        dados = carregar(caminho)
    except ErroEstatisticas as erro:
        print(f"Erro nas estatísticas: {erro}", file=sys.stderr)
        return 1
    if periodo is None:
        exibir_resumo(dados)
    else:
        exibir_periodo(dados, periodo)
    return 0
