import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import player


class TestFormatarTempo(unittest.TestCase):
    def test_formata_duracoes(self):
        casos = [
            (None, "00:00:00"),
            (-10, "00:00:00"),
            (0, "00:00:00"),
            (59.9, "00:00:59"),
            (60, "00:01:00"),
            (3661, "01:01:01"),
        ]

        for segundos, esperado in casos:
            with self.subTest(segundos=segundos):
                self.assertEqual(player.formatar_tempo(segundos), esperado)


class TestListarMusicas(unittest.TestCase):
    def test_descobre_formatos_aceitos_em_ordem(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            nomes = [
                "03-terceira.ogg",
                "01-primeira.mp3",
                "02-segunda.WAV",
                "04-quarta.FlAc",
                "05-quinta.m4a",
                "ignorar.txt",
            ]
            for nome in nomes:
                (pasta / nome).touch()

            with patch.object(player, "PASTA_MUSICAS", diretorio):
                musicas = player.listar_musicas()

        self.assertEqual(
            musicas,
            [
                "01-primeira.mp3",
                "02-segunda.WAV",
                "03-terceira.ogg",
                "04-quarta.FlAc",
                "05-quinta.m4a",
            ],
        )


class TestMenu(unittest.TestCase):
    def test_rejeita_texto_e_numero_fora_da_lista(self):
        saida = io.StringIO()

        with (
            patch.object(player, "listar_musicas", return_value=["musica.mp3"]),
            patch.object(player.os.path, "isdir", return_value=True),
            patch.object(player.shutil, "which", return_value="/usr/bin/mpv"),
            patch.object(player, "exibir_menu"),
            patch("builtins.input", side_effect=["abc", "2", "0"]),
            patch.object(player, "tocar_musicas") as tocar_musicas,
            redirect_stdout(saida),
        ):
            codigo_saida = player.main()

        self.assertEqual(codigo_saida, 0)
        self.assertIn("Opção inválida.", saida.getvalue())
        self.assertIn("Música inválida.", saida.getvalue())
        tocar_musicas.assert_not_called()


class TestComandoMpv(unittest.TestCase):
    def test_monta_comando_e_atalhos_sem_executar_mpv(self):
        processo = Mock()
        processo.poll.return_value = 0
        processo.wait.return_value = 0
        chamada = {}

        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            biblioteca = pasta / "music"
            biblioteca.mkdir()

            def iniciar_mpv(comando):
                chamada["comando"] = comando
                caminho_config = next(
                    item.split("=", 1)[1]
                    for item in comando
                    if item.startswith("--input-conf=")
                )
                caminho_socket = next(
                    item.split("=", 1)[1]
                    for item in comando
                    if item.startswith("--input-ipc-server=")
                )
                chamada["atalhos"] = Path(caminho_config).read_text()
                Path(caminho_socket).touch()
                return processo

            with (
                patch.object(player, "PASTA_MUSICAS", str(biblioteca)),
                patch.object(player.tempfile, "gettempdir", return_value=diretorio),
                patch.object(player.subprocess, "Popen", side_effect=iniciar_mpv),
                patch.object(player, "exibir_reproducao") as exibir_reproducao,
            ):
                codigo_saida = player.tocar_musicas(
                    ["primeira.mp3", "segunda.flac"],
                    1,
                )

        comando = chamada["comando"]
        self.assertEqual(codigo_saida, 0)
        self.assertEqual(comando[0], "mpv")
        self.assertIn("--no-video", comando)
        self.assertIn("--audio-display=no", comando)
        self.assertIn("--loop-playlist=inf", comando)
        self.assertIn("--playlist-start=1", comando)
        self.assertEqual(
            comando[-2:],
            [
                str(biblioteca / "primeira.mp3"),
                str(biblioteca / "segunda.flac"),
            ],
        )
        self.assertEqual(
            chamada["atalhos"].splitlines(),
            [
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
            ],
        )
        exibir_reproducao.assert_called_once()
        processo.wait.assert_called_once_with(timeout=1)


if __name__ == "__main__":
    unittest.main()
