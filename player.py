import os
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time

EXTENSOES = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
ATALHOS = (
    "[P] Pause  [N] proxima  [B] anterior  "
    "[S] aleatorio: {estado}  [Q] sair"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_MUSICAS = os.path.join(BASE_DIR, "music")


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
    return sorted([
        arquivo
        for arquivo in os.listdir(PASTA_MUSICAS)
        if arquivo.lower().endswith(EXTENSOES)
    ])


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


def formatar_controles(aleatorio):
    estado = "ligado" if aleatorio else "desligado"
    return ATALHOS.format(estado=estado)


def exibir_menu(musicas):
    print("\n=== MUSIC PLAYER ===\n")

    for indice, musica in enumerate(musicas, start=1):
        print(f"{indice}. {musica}")

    print("\n0. Sair")


def exibir_reproducao(socket_path, musicas, processo):
    posicao_anterior = None
    status_anterior = None
    aleatorio_anterior = None

    while processo.poll() is None:
        posicao = consultar_mpv(socket_path, "playlist-pos")
        tempo_atual = consultar_mpv(socket_path, "time-pos")
        duracao = consultar_mpv(socket_path, "duration")
        aleatorio = consultar_mpv(socket_path, "shuffle")

        if posicao is not None and posicao != posicao_anterior:
            indice = int(posicao)
            nome = os.path.splitext(musicas[indice])[0]
            status_anterior = None
            aleatorio_anterior = aleatorio
            limpar_tela()
            print(f"Titulo: {nome}")
            print("Tocando: 00:00:00 / 00:00:00")
            print(formatar_controles(aleatorio), flush=True)
            posicao_anterior = posicao

        if aleatorio != aleatorio_anterior and posicao_anterior is not None:
            controles = formatar_controles(aleatorio)
            print(f"\033[1A\r\033[K{controles}\033[K\n", end="", flush=True)
            aleatorio_anterior = aleatorio

        status = (
            f"Tocando: {formatar_tempo(tempo_atual)} / "
            f"{formatar_tempo(duracao)}"
        )

        if status != status_anterior and posicao_anterior is not None:
            print(f"\033[s\033[2A\r\033[K{status}\033[u", end="", flush=True)
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
    socket_path = os.path.join(
        tempfile.gettempdir(),
        f"music-player-{os.getpid()}.sock",
    )
    comandos = "\n".join([
        "p cycle pause",
        "P cycle pause",
        "n playlist-next",
        "N playlist-next",
        "b playlist-prev",
        "B playlist-prev",
        "s cycle shuffle",
        "S cycle shuffle",
        "q quit",
        "Q quit",
    ])

    arquivo_comandos = None
    processo = None
    try:
        arquivo_comandos = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".conf",
            delete=False,
        )
        arquivo_comandos.write(comandos)
        arquivo_comandos.close()

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
                f"--input-ipc-server={socket_path}",
                *playlist,
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

        exibir_reproducao(socket_path, musicas, processo)

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
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except OSError:
                pass


def main():
    if not os.path.isdir(PASTA_MUSICAS):
        print("A pasta 'music' não foi encontrada.", file=sys.stderr)
        return 1

    try:
        musicas = listar_musicas()
    except OSError as erro:
        print(f"Não foi possível ler a pasta 'music': {erro}", file=sys.stderr)
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

    while True:
        exibir_menu(musicas)

        try:
            escolha = input("\nEscolha uma música: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperação cancelada.")
            return 130

        if escolha == "0":
            return 0

        if not escolha.isdigit():
            print("Opção inválida.")
            continue

        indice = int(escolha) - 1

        if 0 <= indice < len(musicas):
            codigo_saida = tocar_musicas(musicas, indice)
            if codigo_saida != 0:
                return codigo_saida
            limpar_tela()
        else:
            print("Música inválida.")


if __name__ == "__main__":
    raise SystemExit(main())
