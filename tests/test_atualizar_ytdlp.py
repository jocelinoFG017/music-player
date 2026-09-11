import hashlib
import io
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import atualizar_ytdlp


class TestChecksum(unittest.TestCase):
    def test_encontra_checksum_do_executavel(self):
        checksum = "a" * 64
        conteudo = f"{'b' * 64}  outro-arquivo\n{checksum} *yt-dlp\n"

        self.assertEqual(atualizar_ytdlp.obter_checksum(conteudo), checksum)

    def test_rejeita_checksum_ausente(self):
        with self.assertRaises(atualizar_ytdlp.ErroAtualizacao):
            atualizar_ytdlp.obter_checksum(f"{'a' * 64}  outro-arquivo\n")


class TestAtualizacao(unittest.TestCase):
    def executar_atualizacao(
        self,
        pasta,
        conteudo_novo,
        checksum=None,
        erro_validacao=None,
    ):
        ytdlp = pasta / "yt-dlp"
        checksum = checksum or hashlib.sha256(conteudo_novo).hexdigest()

        def baixar(url, destino):
            if url == atualizar_ytdlp.URL_CHECKSUMS:
                destino.write_text(f"{checksum}  yt-dlp\n", encoding="utf-8")
            else:
                destino.write_bytes(conteudo_novo)

        with (
            patch.object(atualizar_ytdlp, "PASTA_FERRAMENTAS", pasta),
            patch.object(atualizar_ytdlp, "YTDLP_LOCAL", ytdlp),
            patch.object(atualizar_ytdlp, "baixar_arquivo", side_effect=baixar),
            patch.object(
                atualizar_ytdlp,
                "validar_ytdlp",
                return_value="2026.08.19",
            ) as validar,
            redirect_stdout(io.StringIO()),
        ):
            validar.side_effect = erro_validacao
            retorno = atualizar_ytdlp.atualizar_ytdlp()

        return retorno, ytdlp, validar

    def test_substitui_somente_depois_das_validacoes(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            ytdlp = pasta / "yt-dlp"
            ytdlp.write_bytes(b"versao anterior")
            ytdlp.chmod(0o744)

            retorno, ytdlp, validar = self.executar_atualizacao(
                pasta,
                b"versao nova",
            )

            self.assertEqual(retorno, 0)
            self.assertEqual(ytdlp.read_bytes(), b"versao nova")
            self.assertEqual(stat.S_IMODE(ytdlp.stat().st_mode), 0o744)
            validar.assert_called_once()
            self.assertEqual(
                list(pasta.glob(".atualizacao-yt-dlp-*")),
                [],
            )

    def test_preserva_versao_anterior_se_checksum_falhar(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            ytdlp = pasta / "yt-dlp"
            ytdlp.write_bytes(b"versao anterior")

            with self.assertRaises(atualizar_ytdlp.ErroAtualizacao):
                self.executar_atualizacao(
                    pasta,
                    b"arquivo corrompido",
                    checksum="0" * 64,
                )

            self.assertEqual(ytdlp.read_bytes(), b"versao anterior")

    def test_preserva_versao_anterior_se_execucao_falhar(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            ytdlp = pasta / "yt-dlp"
            ytdlp.write_bytes(b"versao anterior")

            with self.assertRaises(atualizar_ytdlp.ErroAtualizacao):
                self.executar_atualizacao(
                    pasta,
                    b"versao nova",
                    erro_validacao=atualizar_ytdlp.ErroAtualizacao("inválido"),
                )

            self.assertEqual(ytdlp.read_bytes(), b"versao anterior")


if __name__ == "__main__":
    unittest.main()
