import hashlib
import hmac
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
PASTA_FERRAMENTAS = BASE_DIR / ".tools"
YTDLP_LOCAL = PASTA_FERRAMENTAS / "yt-dlp"
URL_RELEASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download"
URL_YTDLP = f"{URL_RELEASE}/yt-dlp"
URL_CHECKSUMS = f"{URL_RELEASE}/SHA2-256SUMS"
NOME_YTDLP = "yt-dlp"


class ErroAtualizacao(Exception):
    pass


def baixar_arquivo(url, destino):
    requisicao = Request(
        url,
        headers={"User-Agent": "music-player-updater/1.0"},
    )
    with urlopen(requisicao, timeout=30) as resposta:
        with destino.open("wb") as arquivo:
            shutil.copyfileobj(resposta, arquivo)


def obter_checksum(conteudo):
    for linha in conteudo.splitlines():
        partes = linha.split()
        if len(partes) < 2 or partes[-1].lstrip("*") != NOME_YTDLP:
            continue

        checksum = partes[0].lower()
        if len(checksum) != 64:
            break
        try:
            int(checksum, 16)
        except ValueError:
            break
        return checksum

    raise ErroAtualizacao(
        "O checksum do yt-dlp não foi encontrado no arquivo oficial."
    )


def calcular_checksum(caminho):
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def validar_ytdlp(caminho):
    try:
        resultado = subprocess.run(
            [sys.executable, str(caminho), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as erro:
        raise ErroAtualizacao(
            f"Não foi possível validar o novo yt-dlp: {erro}"
        ) from erro

    versao = resultado.stdout.strip()
    if resultado.returncode != 0 or not versao:
        detalhe = resultado.stderr.strip() or "resposta sem versão"
        raise ErroAtualizacao(f"O novo yt-dlp falhou na validação: {detalhe}")

    return versao.splitlines()[0]


def atualizar_ytdlp():
    PASTA_FERRAMENTAS.mkdir(parents=True, exist_ok=True)
    modo_anterior = (
        stat.S_IMODE(YTDLP_LOCAL.stat().st_mode)
        if YTDLP_LOCAL.exists()
        else 0o755
    )

    with tempfile.TemporaryDirectory(
        prefix=".atualizacao-yt-dlp-",
        dir=PASTA_FERRAMENTAS,
        ignore_cleanup_errors=True,
    ) as diretorio:
        pasta_temporaria = Path(diretorio)
        caminho_novo = pasta_temporaria / NOME_YTDLP
        caminho_checksums = pasta_temporaria / "SHA2-256SUMS"

        print("Baixando checksums oficiais...")
        baixar_arquivo(URL_CHECKSUMS, caminho_checksums)
        print("Baixando a versão estável mais recente do yt-dlp...")
        baixar_arquivo(URL_YTDLP, caminho_novo)

        try:
            conteudo_checksums = caminho_checksums.read_text(encoding="utf-8")
        except UnicodeError as erro:
            raise ErroAtualizacao(
                "O arquivo oficial de checksums não é um texto válido."
            ) from erro

        checksum_esperado = obter_checksum(conteudo_checksums)
        checksum_recebido = calcular_checksum(caminho_novo)
        if not hmac.compare_digest(checksum_recebido, checksum_esperado):
            raise ErroAtualizacao(
                "O SHA-256 do arquivo baixado não corresponde ao oficial."
            )

        os.chmod(caminho_novo, modo_anterior)
        versao = validar_ytdlp(caminho_novo)
        os.replace(caminho_novo, YTDLP_LOCAL)

    print(f"yt-dlp atualizado com segurança para a versão {versao}.")
    return 0


def main():
    try:
        return atualizar_ytdlp()
    except KeyboardInterrupt:
        print("\nAtualização cancelada; a versão anterior foi preservada.")
        return 130
    except (ErroAtualizacao, OSError, URLError) as erro:
        print(
            f"Atualização não concluída: {erro}\n"
            "A versão anterior do yt-dlp foi preservada.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
