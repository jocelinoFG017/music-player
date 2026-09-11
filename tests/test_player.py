import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

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


class TestInicializacao(unittest.TestCase):
    def test_inicia_primeira_musica_sem_pedir_escolha(self):
        musicas = ["01-primeira.mp3", "02-segunda.mp3"]

        with (
            patch.object(player, "listar_musicas", return_value=musicas),
            patch.object(player.os.path, "isdir", return_value=True),
            patch.object(player.shutil, "which", return_value="/usr/bin/mpv"),
            patch.object(player, "tocar_musicas", return_value=0) as tocar,
            patch("builtins.input") as entrada,
        ):
            codigo_saida = player.main()

        self.assertEqual(codigo_saida, 0)
        tocar.assert_called_once_with(musicas, 0)
        entrada.assert_not_called()


class TestListaDuranteReproducao(unittest.TestCase):
    def test_exibe_lista_e_destaca_musica_atual(self):
        saida = io.StringIO()

        with redirect_stdout(saida):
            player.exibir_lista_reproducao(
                ["primeira.mp3", "segunda.flac"],
                1,
                False,
            )

        texto = saida.getvalue()
        self.assertIn("  1. primeira", texto)
        self.assertIn("> 2. segunda", texto)
        self.assertIn("[L] voltar", texto)

    def test_consumir_pedido_remove_arquivo(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pedido = Path(diretorio) / "listar"
            pedido.touch()

            self.assertTrue(player.consumir_pedido_de_lista(str(pedido)))
            self.assertFalse(pedido.exists())
            self.assertFalse(player.consumir_pedido_de_lista(str(pedido)))


class TestModoAleatorio(unittest.TestCase):
    def test_reordena_playlist_ao_ligar_e_restaura_ao_desligar(self):
        musicas = ["primeira.mp3", "segunda.mp3"]
        embaralhadas = ["segunda.mp3", "primeira.mp3"]

        with (
            patch.object(
                player,
                "enviar_comando_mpv",
                return_value=True,
            ) as enviar,
            patch.object(
                player,
                "obter_musicas_da_playlist",
                side_effect=[embaralhadas, musicas],
            ),
        ):
            resultado_ligado = player.reordenar_playlist(
                "/tmp/mpv.sock",
                True,
                musicas,
            )
            resultado_desligado = player.reordenar_playlist(
                "/tmp/mpv.sock",
                False,
                embaralhadas,
            )

        self.assertEqual(resultado_ligado, embaralhadas)
        self.assertEqual(resultado_desligado, musicas)
        self.assertEqual(
            enviar.call_args_list,
            [
                call("/tmp/mpv.sock", ["playlist-shuffle"]),
                call("/tmp/mpv.sock", ["playlist-unshuffle"]),
            ],
        )

    def test_sincroniza_nomes_com_a_ordem_do_mpv(self):
        playlist = [
            {"filename": "/musicas/segunda.flac"},
            {"filename": "/musicas/primeira.mp3"},
        ]

        with patch.object(player, "consultar_mpv", return_value=playlist):
            musicas = player.obter_musicas_da_playlist(
                "/tmp/mpv.sock",
                ["primeira.mp3", "segunda.flac"],
            )

        self.assertEqual(musicas, ["segunda.flac", "primeira.mp3"])


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
                chamada["socket"] = caminho_socket
                chamada["atalhos"] = Path(caminho_config).read_text()
                Path(caminho_socket).touch()
                return processo

            with (
                patch.object(player, "PASTA_MUSICAS", str(biblioteca)),
                patch.object(player.tempfile, "gettempdir", return_value=diretorio),
                patch.object(
                    player.shutil,
                    "which",
                    return_value="/usr/bin/touch",
                ),
                patch.object(player.subprocess, "Popen", side_effect=iniciar_mpv),
                patch.object(player, "exibir_reproducao") as exibir_reproducao,
            ):
                codigo_saida = player.tocar_musicas(
                    ["primeira.mp3", "segunda.flac"],
                    1,
                )

        comando = chamada["comando"]
        caminho_socket = chamada["socket"]
        caminho_pedido = caminho_socket.removesuffix(".sock") + "-listar"
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
                f'l run "/usr/bin/touch" "{caminho_pedido}"',
                f'L run "/usr/bin/touch" "{caminho_pedido}"',
                "q quit",
                "Q quit",
            ],
        )
        exibir_reproducao.assert_called_once_with(
            caminho_socket,
            ["primeira.mp3", "segunda.flac"],
            processo,
            caminho_pedido,
        )
        processo.wait.assert_called_once_with(timeout=1)


if __name__ == "__main__":
    unittest.main()
