import os
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata

EXTENSOES = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
LARGURA_MAXIMA = 110

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_MUSICAS = os.path.join(BASE_DIR, "music")

SCRIPT_NAVEGACAO = r'''
local mp = require "mp"

math.randomseed(os.time() + math.floor(mp.get_time() * 1000000))

local function navegar(comando_sequencial)
    if not mp.get_property_native("shuffle", false) then
        mp.commandv(comando_sequencial)
        return
    end

    local total = mp.get_property_number("playlist-count", 0)
    local atual = mp.get_property_number("playlist-pos", 0)
    if total <= 1 then
        return
    end

    local destino = math.random(0, total - 2)
    if destino >= atual then
        destino = destino + 1
    end
    mp.set_property_number("playlist-pos", destino)
end

mp.add_forced_key_binding("n", "music-player-next", function()
    navegar("playlist-next")
end)
mp.add_forced_key_binding("N", "music-player-next-upper", function()
    navegar("playlist-next")
end)
mp.add_forced_key_binding("b", "music-player-prev", function()
    navegar("playlist-prev")
end)
mp.add_forced_key_binding("B", "music-player-prev-upper", function()
    navegar("playlist-prev")
end)
'''.strip()


def limpar_tela():
    if not sys.stdout.isatty():
        return

    comando = "cls" if os.name == "nt" else "clear"
    try:
        if os.name == "nt":
            subprocess.run(["cmd", "/c", comando], check=False)
        elif shutil.which(comando):
            subprocess.run([comando], check=False)
    except OSError:
        pass


def listar_musicas():
    return sorted(
        [
            arquivo
            for arquivo in os.listdir(PASTA_MUSICAS)
            if arquivo.lower().endswith(EXTENSOES)
        ],
        key=str.casefold,
    )


def formatar_tempo(segundos):
    if segundos is None:
        return "00:00:00"

    total_segundos = max(0, int(segundos))
    horas, restante = divmod(total_segundos, 3600)
    minutos, segundos = divmod(restante, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def consultar_mpv(socket_path, propriedade):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conexao:
            conexao.settimeout(0.2)
            conexao.connect(socket_path)
            comando = json.dumps({
                "command": ["get_property", propriedade]
            }).encode() + b"\n"
            conexao.sendall(comando)
            resposta = conexao.recv(4096)
            return json.loads(resposta.decode()).get("data")
    except (ConnectionError, OSError, json.JSONDecodeError):
        return None


def largura_visual(texto):
    return sum(
        0 if unicodedata.combining(caractere)
        else 2 if unicodedata.east_asian_width(caractere) in ("W", "F")
        else 1
        for caractere in texto
    )


def ajustar_texto(texto, largura):
    if largura <= 0:
        return ""

    if largura_visual(texto) <= largura:
        return texto + " " * (largura - largura_visual(texto))

    if largura == 1:
        return "…"

    caracteres = []
    largura_usada = 0
    for caractere in texto:
        largura_caractere = largura_visual(caractere)
        if largura_usada + largura_caractere > largura - 1:
            break
        caracteres.append(caractere)
        largura_usada += largura_caractere

    resultado = "".join(caracteres) + "…"
    return resultado + " " * (largura - largura_visual(resultado))


def obter_dimensoes_terminal():
    dimensoes = shutil.get_terminal_size(fallback=(100, 24))
    largura = max(24, min(dimensoes.columns, LARGURA_MAXIMA))
    altura = max(8, dimensoes.lines)
    return largura, altura


def formatar_controles(aleatorio, lista_visivel=False, largura=100):
    estado = "ligado" if aleatorio else "desligado"
    if largura < 48:
        estado_curto = "on" if aleatorio else "off"
        texto = (
            f"N/B S:{estado_curto} Pg↑/Pg↓ L Q"
            if lista_visivel
            else f"P N/B S:{estado_curto} L Q"
        )
    elif lista_visivel:
        texto = (
            f"[N/B] faixa  [S] aleatório: {estado}  "
            "[PgUp/PgDn] páginas  [L] voltar  [Q] sair"
        )
    else:
        texto = (
            f"[P] pausa  [N/B] faixa  [S] aleatório: {estado}  "
            "[L] biblioteca  [Q] sair"
        )
    return ajustar_texto(texto, largura).rstrip()


def criar_borda(titulo, largura, superior=True):
    esquerda, direita, traco = ("╭", "╮", "─") if superior else ("╰", "╯", "─")
    if not titulo:
        return esquerda + traco * (largura - 2) + direita

    rotulo_original = f"─ {titulo} "
    if largura_visual(rotulo_original) > largura - 2:
        rotulo = ajustar_texto(rotulo_original, largura - 2).rstrip()
    else:
        rotulo = rotulo_original
    restante = max(0, largura - largura_visual(rotulo) - 2)
    return esquerda + rotulo + traco * restante + direita


def formatar_progresso(tempo_atual, duracao, largura):
    atual = formatar_tempo(tempo_atual)
    total = formatar_tempo(duracao)
    largura_barra = max(3, largura - len(atual) - len(total) - 5)
    proporcao = 0 if not duracao else min(1, max(0, (tempo_atual or 0) / duracao))
    preenchido = min(largura_barra, int(proporcao * largura_barra))
    barra = "━" * preenchido + "─" * (largura_barra - preenchido)
    return ajustar_texto(f" {atual} {barra} {total}", largura)


def exibir_painel_reproducao(nome, tempo_atual, duracao, aleatorio, largura):
    interior = largura - 2
    print(criar_borda("TOCANDO AGORA", largura))
    print(f"│{ajustar_texto(f'  ♫  {nome}', interior)}│")
    print(f"│{formatar_progresso(tempo_atual, duracao, interior)}│")
    print(criar_borda("", largura, superior=False))
    print(formatar_controles(aleatorio, largura=largura), flush=True)


def calcular_paginacao(total, pagina, altura):
    itens_por_pagina = max(3, altura - 5)
    total_paginas = max(1, (total + itens_por_pagina - 1) // itens_por_pagina)
    pagina = min(max(0, pagina), total_paginas - 1)
    inicio = pagina * itens_por_pagina
    fim = min(total, inicio + itens_por_pagina)
    return pagina, total_paginas, inicio, fim


def exibir_lista_reproducao(
    musicas,
    posicao,
    aleatorio,
    pagina=0,
    dimensoes=None,
):
    largura, altura = dimensoes or obter_dimensoes_terminal()
    pagina, total_paginas, inicio, fim = calcular_paginacao(
        len(musicas),
        pagina,
        altura,
    )
    digitos = len(str(len(musicas)))
    titulo = (
        f"BIBLIOTECA · {len(musicas)} músicas · "
        f"página {pagina + 1}/{total_paginas}"
    )
    print(criar_borda(titulo, largura))

    for indice in range(inicio, fim):
        musica = musicas[indice]
        marcador = "▶" if indice == posicao else " "
        nome = os.path.splitext(musica)[0]
        conteudo = f" {marcador} {indice + 1:0{digitos}d}  {nome}"
        print(f"│{ajustar_texto(conteudo, largura - 2)}│")

    print(criar_borda("", largura, superior=False))
    print(
        formatar_controles(
            aleatorio,
            lista_visivel=True,
            largura=largura,
        ),
        flush=True,
    )
    return pagina


def consumir_pedido(caminho_pedido):
    try:
        os.unlink(caminho_pedido)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def exibir_reproducao(socket_path, musicas, processo, caminhos_pedidos):
    posicao_anterior = None
    status_anterior = None
    aleatorio_anterior = None
    lista_visivel = False
    pagina_lista = 0
    dimensoes_anteriores = None

    while processo.poll() is None:
        dimensoes = obter_dimensoes_terminal()
        mudou_dimensoes = dimensoes != dimensoes_anteriores
        dimensoes_anteriores = dimensoes
        posicao = consultar_mpv(socket_path, "playlist-pos")
        tempo_atual = consultar_mpv(socket_path, "time-pos")
        duracao = consultar_mpv(socket_path, "duration")
        aleatorio = consultar_mpv(socket_path, "shuffle")
        if aleatorio is None and aleatorio_anterior is not None:
            aleatorio = aleatorio_anterior
        alternou_lista = consumir_pedido(caminhos_pedidos["lista"])
        pagina_anterior = consumir_pedido(
            caminhos_pedidos["pagina_anterior"],
        )
        proxima_pagina = consumir_pedido(
            caminhos_pedidos["proxima_pagina"],
        )

        if alternou_lista:
            lista_visivel = not lista_visivel
            posicao_anterior = None
            status_anterior = None
            limpar_tela()

        mudou_musica = posicao is not None and posicao != posicao_anterior
        mudou_aleatorio = aleatorio != aleatorio_anterior

        if lista_visivel:
            itens_por_pagina = max(3, dimensoes[1] - 5)
            if posicao is not None and (
                mudou_musica or alternou_lista or mudou_dimensoes
            ):
                pagina_lista = int(posicao) // itens_por_pagina
            if pagina_anterior:
                pagina_lista -= 1
            if proxima_pagina:
                pagina_lista += 1

            if posicao is not None and (
                alternou_lista
                or mudou_musica
                or mudou_aleatorio
                or pagina_anterior
                or proxima_pagina
                or mudou_dimensoes
            ):
                limpar_tela()
                pagina_lista = exibir_lista_reproducao(
                    musicas,
                    int(posicao),
                    aleatorio,
                    pagina=pagina_lista,
                    dimensoes=dimensoes,
                )
                posicao_anterior = posicao
                aleatorio_anterior = aleatorio
            time.sleep(0.2)
            continue

        renderizou_painel = False
        if posicao is not None and (
            mudou_musica or alternou_lista or mudou_dimensoes
        ):
            indice = int(posicao)
            nome = os.path.splitext(musicas[indice])[0]
            aleatorio_anterior = aleatorio
            limpar_tela()
            exibir_painel_reproducao(
                nome,
                tempo_atual,
                duracao,
                aleatorio,
                dimensoes[0],
            )
            status_anterior = formatar_progresso(
                tempo_atual,
                duracao,
                dimensoes[0] - 2,
            )
            posicao_anterior = posicao
            renderizou_painel = True

        if (
            mudou_aleatorio
            and posicao_anterior is not None
            and not renderizou_painel
        ):
            controles = formatar_controles(aleatorio, largura=dimensoes[0])
            print(f"\033[1A\r\033[K{controles}\033[K\n", end="", flush=True)
            aleatorio_anterior = aleatorio

        status = formatar_progresso(
            tempo_atual,
            duracao,
            dimensoes[0] - 2,
        )

        if (
            status != status_anterior
            and posicao_anterior is not None
            and not renderizou_painel
        ):
            print(
                f"\033[s\033[3A\r\033[K│{status}│\033[u",
                end="",
                flush=True,
            )
            status_anterior = status

        if not os.path.exists(socket_path):
            break

        time.sleep(0.2)


def encerrar_processo(processo):
    if processo.poll() is not None:
        return

    try:
        processo.terminate()
    except ProcessLookupError:
        return

    try:
        processo.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            processo.kill()
        except ProcessLookupError:
            return
        processo.wait()


def tocar_musicas(musicas, indice_inicial):
    playlist = [os.path.join(PASTA_MUSICAS, musica) for musica in musicas]
    identificador = f"{os.getpid()}-{time.monotonic_ns()}"
    prefixo_controle = os.path.join(
        tempfile.gettempdir(),
        f"music-player-{identificador}",
    )
    socket_path = os.path.join(
        tempfile.gettempdir(),
        f"music-player-{identificador}.sock",
    )
    caminhos_pedidos = {
        "lista": f"{prefixo_controle}-listar",
        "pagina_anterior": f"{prefixo_controle}-pagina-anterior",
        "proxima_pagina": f"{prefixo_controle}-proxima-pagina",
    }
    comando_touch = shutil.which("touch") or "/usr/bin/touch"
    for caminho in caminhos_pedidos.values():
        consumir_pedido(caminho)
    comandos = "\n".join([
        "p cycle pause",
        "P cycle pause",
        "s cycle shuffle",
        "S cycle shuffle",
        f'l run "{comando_touch}" "{caminhos_pedidos["lista"]}"',
        f'L run "{comando_touch}" "{caminhos_pedidos["lista"]}"',
        (
            f'PGUP run "{comando_touch}" '
            f'"{caminhos_pedidos["pagina_anterior"]}"'
        ),
        (
            f'PGDWN run "{comando_touch}" '
            f'"{caminhos_pedidos["proxima_pagina"]}"'
        ),
        "q quit",
        "Q quit",
    ])

    arquivo_comandos = None
    arquivo_script = None
    arquivo_playlist = None
    processo = None
    try:
        arquivo_comandos = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".conf",
            delete=False,
        )
        arquivo_comandos.write(comandos)
        arquivo_comandos.close()

        arquivo_script = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".lua",
            delete=False,
        )
        arquivo_script.write(SCRIPT_NAVEGACAO)
        arquivo_script.close()

        arquivo_playlist = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".m3u8",
            encoding="utf-8",
            delete=False,
        )
        arquivo_playlist.write("#EXTM3U\n")
        arquivo_playlist.writelines(f"{caminho}\n" for caminho in playlist)
        arquivo_playlist.close()

        try:
            processo = subprocess.Popen([
                "mpv",
                "--no-video",
                "--audio-display=no",
                "--cover-art-auto=no",
                "--msg-level=all=error",
                "--loop-playlist=inf",
                f"--playlist-start={indice_inicial}",
                f"--input-conf={arquivo_comandos.name}",
                f"--script={arquivo_script.name}",
                f"--input-ipc-server={socket_path}",
                f"--playlist={arquivo_playlist.name}",
            ])
        except OSError as erro:
            print(f"Não foi possível iniciar o mpv: {erro}", file=sys.stderr)
            return 1

        limite = time.monotonic() + 2
        while not os.path.exists(socket_path) and processo.poll() is None:
            if time.monotonic() >= limite:
                break
            time.sleep(0.05)

        if not os.path.exists(socket_path):
            codigo_saida = processo.poll()
            if codigo_saida is None:
                print(
                    "O mpv iniciou, mas o controle da reprodução não ficou "
                    "disponível.",
                    file=sys.stderr,
                )
                encerrar_processo(processo)
                return 1

            print(
                f"O mpv encerrou antes de iniciar a reprodução "
                f"(código {codigo_saida}).",
                file=sys.stderr,
            )
            return codigo_saida if codigo_saida > 0 else 1

        exibir_reproducao(
            socket_path,
            musicas,
            processo,
            caminhos_pedidos,
        )

        try:
            codigo_saida = processo.wait(timeout=1)
        except subprocess.TimeoutExpired:
            print(
                "A conexão com o mpv foi perdida durante a reprodução.",
                file=sys.stderr,
            )
            encerrar_processo(processo)
            return 1

        if codigo_saida != 0:
            print(
                f"O mpv encerrou com erro (código {codigo_saida}).",
                file=sys.stderr,
            )
            return codigo_saida if codigo_saida > 0 else 1

        return 0
    except KeyboardInterrupt:
        if processo is not None:
            encerrar_processo(processo)
        print("\nReprodução cancelada.")
        return 130
    except OSError as erro:
        if processo is not None:
            encerrar_processo(processo)
        print(f"Erro ao preparar a reprodução: {erro}", file=sys.stderr)
        return 1
    finally:
        if processo is not None:
            encerrar_processo(processo)
        if arquivo_comandos is not None and not arquivo_comandos.closed:
            try:
                arquivo_comandos.close()
            except OSError:
                pass
        if arquivo_comandos is not None:
            try:
                os.unlink(arquivo_comandos.name)
            except FileNotFoundError:
                pass
        if arquivo_script is not None and not arquivo_script.closed:
            try:
                arquivo_script.close()
            except OSError:
                pass
        if arquivo_script is not None:
            try:
                os.unlink(arquivo_script.name)
            except FileNotFoundError:
                pass
        if arquivo_playlist is not None and not arquivo_playlist.closed:
            try:
                arquivo_playlist.close()
            except OSError:
                pass
        if arquivo_playlist is not None:
            try:
                os.unlink(arquivo_playlist.name)
            except FileNotFoundError:
                pass
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except OSError:
                pass
        for caminho in caminhos_pedidos.values():
            if os.path.exists(caminho):
                try:
                    os.unlink(caminho)
                except OSError:
                    pass


def main():
    if not os.path.isdir(PASTA_MUSICAS):
        print("A pasta 'music' não foi encontrada.", file=sys.stderr)
        return 1

    try:
        musicas = listar_musicas()
    except OSError as erro:
        print(
            f"Não foi possível ler a pasta 'music': {erro}",
            file=sys.stderr,
        )
        return 1

    if not musicas:
        print("Nenhuma música encontrada.")
        return 0

    if shutil.which("mpv") is None:
        print(
            "O mpv não foi encontrado. Instale-o antes de continuar.",
            file=sys.stderr,
        )
        return 1

    return tocar_musicas(musicas, 0)


if __name__ == "__main__":
    raise SystemExit(main())
