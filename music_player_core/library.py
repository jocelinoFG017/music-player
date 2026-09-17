import json
import os
import tempfile
from pathlib import Path


EXTENSOES_AUDIO = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def _diretorio_configuracao():
    personalizado = os.environ.get("MUSIC_PLAYER_CONFIG_DIR")
    if personalizado:
        return Path(personalizado).expanduser()
    base_xdg = os.environ.get("XDG_CONFIG_HOME")
    if base_xdg:
        return Path(base_xdg).expanduser() / "music-player"
    return Path.home() / ".config" / "music-player"


CAMINHO_CONFIGURACAO = _diretorio_configuracao() / "config.json"


def carregar_configuracao():
    try:
        with CAMINHO_CONFIGURACAO.open(encoding="utf-8") as arquivo:
            configuracao = json.load(arquivo)
        return configuracao if isinstance(configuracao, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def salvar_configuracao(**alteracoes):
    configuracao = carregar_configuracao()
    configuracao.update(alteracoes)
    CAMINHO_CONFIGURACAO.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        temporario = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".config-",
            suffix=".tmp",
            dir=CAMINHO_CONFIGURACAO.parent,
            delete=False,
        )
        json.dump(configuracao, temporario, ensure_ascii=False, indent=2)
        temporario.write("\n")
        temporario.flush()
        os.fsync(temporario.fileno())
        temporario.close()
        os.replace(temporario.name, CAMINHO_CONFIGURACAO)
        temporario = None
    finally:
        if temporario is not None:
            try:
                nome = temporario.name
                if not temporario.closed:
                    temporario.close()
                os.unlink(nome)
            except OSError:
                pass


def pasta_musicas():
    """Retorna a biblioteca comum aos dois players.

    A variável de ambiente é útil para uma execução pontual. A configuração
    persistente fica fora do repositório e pode ser usada tanto pelo CLI quanto
    pelo GUI.
    """
    personalizada = os.environ.get("MUSIC_PLAYER_LIBRARY")
    if personalizada:
        return Path(personalizada).expanduser().resolve()

    configurada = carregar_configuracao().get("library_path")
    if configurada:
        return Path(configurada).expanduser().resolve()

    return RAIZ_PROJETO / "music"


def pasta_downloads_configurada():
    configurada = carregar_configuracao().get("download_path")
    if not configurada:
        return None
    return Path(configurada).expanduser().resolve()


def listar_musicas(diretorio=None):
    diretorio = Path(diretorio or pasta_musicas())
    musicas = []
    for raiz, _, arquivos in os.walk(diretorio):
        raiz = Path(raiz)
        for arquivo in arquivos:
            if arquivo.lower().endswith(EXTENSOES_AUDIO):
                musicas.append((raiz / arquivo).relative_to(diretorio).as_posix())
    return sorted(musicas, key=str.casefold)
