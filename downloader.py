import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
PASTA_DOWNLOADS = BASE_DIR / "download-direto"
YTDLP_LOCAL = BASE_DIR / ".tools" / "yt-dlp"


def criar_parser():
    parser = argparse.ArgumentParser(
        description="Baixa o áudio de um vídeo do YouTube em formato MP3.",
    )
    parser.add_argument(
        "link",
        nargs="?",
        help="link do vídeo no YouTube",
    )
    return parser


def link_do_youtube(link):
    try:
        endereco = urlparse(link)
    except ValueError:
        return False

    host = (endereco.hostname or "").lower()
    host_valido = (
        host == "youtu.be"
        or host == "youtube.com"
        or host.endswith(".youtube.com")
    )
    return endereco.scheme in ("http", "https") and host_valido


def obter_link(link_informado):
    if link_informado:
        return link_informado.strip()
    return input("Cole o link do YouTube: ").strip()


def baixar_mp3(link):
    if not YTDLP_LOCAL.is_file():
        print(
            f"O yt-dlp local não foi encontrado em: {YTDLP_LOCAL}",
            file=sys.stderr,
        )
        return 1

    if shutil.which("ffmpeg") is None:
        print(
            "O ffmpeg não foi encontrado. Instale-o antes de continuar.",
            file=sys.stderr,
        )
        return 1

    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    modelo_saida = str(PASTA_DOWNLOADS / "%(title)s [%(id)s].%(ext)s")
    comando = [
        sys.executable,
        str(YTDLP_LOCAL),
        "--ignore-config",
        "--no-playlist",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--format",
        "bestaudio/best",
        "--output",
        modelo_saida,
        "--",
        link,
    ]

    try:
        resultado = subprocess.run(comando, check=False)
    except OSError as erro:
        print(f"Não foi possível executar o yt-dlp: {erro}", file=sys.stderr)
        return 1

    if resultado.returncode != 0:
        print("O download não foi concluído.", file=sys.stderr)
        return resultado.returncode

    print(f"MP3 salvo em: {PASTA_DOWNLOADS}")
    return 0


def main():
    argumentos = criar_parser().parse_args()

    try:
        link = obter_link(argumentos.link)
    except (EOFError, KeyboardInterrupt):
        print("\nOperação cancelada.")
        return 130

    if not link_do_youtube(link):
        print("Informe um link válido do YouTube.", file=sys.stderr)
        return 2

    return baixar_mp3(link)


if __name__ == "__main__":
    raise SystemExit(main())
