import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from music_player_core.library import pasta_downloads_configurada


BASE_DIR = Path(__file__).resolve().parent
PASTA_DOWNLOADS = pasta_downloads_configurada() or BASE_DIR / "download-direto"
YTDLP_LOCAL = BASE_DIR / ".tools" / "yt-dlp"
MARCADOR_ARQUIVO = "__MUSIC_PLAYER_FILE__"
PADRAO_ID_FINAL = re.compile(r"^(?P<titulo>.+) \[[^\[\]]+\]$")


class ErroDownload(Exception):
    pass


def criar_parser():
    parser = argparse.ArgumentParser(
        description="Baixa o áudio de um vídeo do YouTube em formato MP3.",
    )
    parser.add_argument(
        "link",
        nargs="?",
        help="link do vídeo no YouTube",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="pasta em que o MP3 será salvo",
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


def preparar_download(link, pasta_downloads=None):
    if not YTDLP_LOCAL.is_file():
        raise ErroDownload(
            f"O yt-dlp local não foi encontrado em: {YTDLP_LOCAL}"
        )

    if shutil.which("ffmpeg") is None:
        raise ErroDownload(
            "O ffmpeg não foi encontrado. Instale-o antes de continuar."
        )

    destino = Path(pasta_downloads or PASTA_DOWNLOADS).expanduser().resolve()
    destino.mkdir(parents=True, exist_ok=True)
    modelo_saida = str(destino / "%(title)s [%(id)s].%(ext)s")
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
        "--print",
        f"after_move:{MARCADOR_ARQUIVO}%(filepath)s",
        "--",
        link,
    ]
    return comando, destino


def _proximo_nome_disponivel(caminho):
    if not caminho.exists():
        return caminho
    numero = 2
    while True:
        candidato = caminho.with_name(
            f"{caminho.stem} ({numero}){caminho.suffix}"
        )
        if not candidato.exists():
            return candidato
        numero += 1


def remover_id_do_nome(caminho):
    caminho = Path(caminho)
    correspondencia = PADRAO_ID_FINAL.match(caminho.stem)
    if correspondencia is None:
        return caminho
    destino = caminho.with_name(
        f"{correspondencia.group('titulo')}{caminho.suffix}"
    )
    destino = _proximo_nome_disponivel(destino)
    caminho.rename(destino)
    return destino


def finalizar_download(saida, pasta_downloads):
    for linha in reversed((saida or "").splitlines()):
        if not linha.startswith(MARCADOR_ARQUIVO):
            continue
        caminho = Path(linha.removeprefix(MARCADOR_ARQUIVO))
        if caminho.parent.resolve() != Path(pasta_downloads).resolve():
            raise ErroDownload("O yt-dlp informou um destino inesperado.")
        if not caminho.is_file():
            raise ErroDownload("O arquivo baixado não foi encontrado.")
        return remover_id_do_nome(caminho)
    raise ErroDownload("O yt-dlp não informou o nome do arquivo baixado.")


def baixar_mp3(link, pasta_downloads=None):
    try:
        comando, destino = preparar_download(link, pasta_downloads)
    except (ErroDownload, OSError) as erro:
        print(str(erro), file=sys.stderr)
        return 1

    try:
        resultado = subprocess.run(
            comando,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as erro:
        print(f"Não foi possível executar o yt-dlp: {erro}", file=sys.stderr)
        return 1

    if resultado.returncode != 0:
        if resultado.stderr:
            print(resultado.stderr.strip(), file=sys.stderr)
        print("O download não foi concluído.", file=sys.stderr)
        return resultado.returncode

    try:
        caminho_final = finalizar_download(resultado.stdout, destino)
    except (ErroDownload, OSError) as erro:
        print(f"Download concluído, mas o arquivo não foi renomeado: {erro}")
        return 1

    print(f"MP3 salvo em: {caminho_final}")
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

    return baixar_mp3(link, argumentos.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
