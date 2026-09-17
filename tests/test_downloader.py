import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import downloader


class TestLinkDoYoutube(unittest.TestCase):
    def test_aceita_hosts_do_youtube(self):
        links = [
            "https://www.youtube.com/watch?v=video",
            "http://youtube.com/watch?v=video",
            "https://music.youtube.com/watch?v=video",
            "https://youtu.be/video",
        ]

        for link in links:
            with self.subTest(link=link):
                self.assertTrue(downloader.link_do_youtube(link))

    def test_rejeita_links_invalidos(self):
        links = [
            "",
            "youtube.com/watch?v=video",
            "ftp://youtube.com/watch?v=video",
            "https://example.com/video",
            "https://youtube.com.exemplo.com/video",
            "https://youtu.be.exemplo.com/video",
            "https://[endereco-invalido",
        ]

        for link in links:
            with self.subTest(link=link):
                self.assertFalse(downloader.link_do_youtube(link))


class TestComandoYtDlp(unittest.TestCase):
    def test_monta_comando_sem_executar_download(self):
        link = "https://www.youtube.com/watch?v=video"

        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            ytdlp = pasta / "yt-dlp"
            downloads = pasta / "downloads"
            ytdlp.touch()
            downloads.mkdir()
            arquivo_baixado = downloads / "Faixa [video].mp3"
            arquivo_baixado.touch()
            resultado = subprocess.CompletedProcess(
                [],
                0,
                stdout=(
                    f"{downloader.MARCADOR_ARQUIVO}{arquivo_baixado}\n"
                ),
                stderr="",
            )

            with (
                patch.object(downloader, "YTDLP_LOCAL", ytdlp),
                patch.object(
                    downloader.shutil,
                    "which",
                    return_value="/usr/bin/ffmpeg",
                ),
                patch.object(
                    downloader.subprocess,
                    "run",
                    return_value=resultado,
                ) as executar,
                redirect_stdout(io.StringIO()),
            ):
                codigo_saida = downloader.baixar_mp3(link, downloads)

            modelo_saida = str(
                downloads / "%(title)s [%(id)s].%(ext)s"
            )
            comando_esperado = [
                sys.executable,
                str(ytdlp),
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
                (
                    "after_move:"
                    f"{downloader.MARCADOR_ARQUIVO}%(filepath)s"
                ),
                "--",
                link,
            ]
            arquivo_final_existe = (downloads / "Faixa.mp3").is_file()

        self.assertEqual(codigo_saida, 0)
        executar.assert_called_once_with(
            comando_esperado,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(arquivo_final_existe)

    def test_remove_id_sem_sobrescrever_arquivo_existente(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            (pasta / "Faixa.mp3").touch()
            baixado = pasta / "Faixa [video].mp3"
            baixado.touch()

            caminho_final = downloader.finalizar_download(
                f"{downloader.MARCADOR_ARQUIVO}{baixado}\n",
                pasta,
            )

        self.assertEqual(caminho_final.name, "Faixa (2).mp3")


if __name__ == "__main__":
    unittest.main()
