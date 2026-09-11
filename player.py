import os
import json
import socket
import subprocess
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
    comando = "cls" if os.name == "nt" else "clear"
    subprocess.run([comando], check=False)


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

    arquivo_comandos = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".conf",
        delete=False,
    )
    try:
        arquivo_comandos.write(comandos)
        arquivo_comandos.close()

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

        limite = time.monotonic() + 2
        while not os.path.exists(socket_path) and processo.poll() is None:
            if time.monotonic() >= limite:
                break
            time.sleep(0.05)

        if os.path.exists(socket_path):
            exibir_reproducao(socket_path, musicas, processo)

        processo.wait()
    finally:
        os.unlink(arquivo_comandos.name)
        if os.path.exists(socket_path):
            os.unlink(socket_path)


def main():
    if not os.path.isdir(PASTA_MUSICAS):
        print("A pasta 'music' não foi encontrada.")
        return

    musicas = listar_musicas()

    if not musicas:
        print("Nenhuma música encontrada.")
        return

    while True:
        exibir_menu(musicas)

        escolha = input("\nEscolha uma música: ").strip()

        if escolha == "0":
            break

        if not escolha.isdigit():
            print("Opção inválida.")
            continue

        indice = int(escolha) - 1

        if 0 <= indice < len(musicas):
            tocar_musicas(musicas, indice)
            limpar_tela()
        else:
            print("Música inválida.")


if __name__ == "__main__":
    main()
