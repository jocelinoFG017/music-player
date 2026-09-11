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
                dimensoes=(80, 12),
            )

        texto = saida.getvalue()
        self.assertIn("BIBLIOTECA · 2 músicas · página 1/1", texto)
        self.assertIn("  1  primeira", texto)
        self.assertIn("▶ 2  segunda", texto)
        self.assertIn("[L] voltar", texto)

    def test_consumir_pedido_remove_arquivo(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pedido = Path(diretorio) / "listar"
            pedido.touch()

            self.assertTrue(player.consumir_pedido(str(pedido)))
            self.assertFalse(pedido.exists())
            self.assertFalse(player.consumir_pedido(str(pedido)))

    def test_pagina_lista_grande_sem_imprimir_todas_as_musicas(self):
        musicas = [f"musica-{indice:03d}.mp3" for indice in range(1, 501)]
        saida = io.StringIO()

        with redirect_stdout(saida):
            pagina = player.exibir_lista_reproducao(
                musicas,
                72,
                True,
                pagina=10,
                dimensoes=(70, 12),
            )

        texto = saida.getvalue()
        self.assertEqual(pagina, 10)
        self.assertIn("500 músicas · página 11/72", texto)
        self.assertIn("▶ 073  musica-073", texto)
        self.assertNotIn("musica-001", texto)
        self.assertNotIn("musica-500", texto)
        self.assertLessEqual(len(texto.splitlines()), 11)

    def test_encurta_titulo_longo_respeitando_caracteres_largos(self):
        titulo = player.ajustar_texto("僕は雨になりたい e continuar", 12)

        self.assertEqual(player.largura_visual(titulo), 12)
        self.assertTrue(titulo.rstrip().endswith("…"))

    def test_cabecalho_e_controles_cabem_em_terminal_estreito(self):
        borda = player.criar_borda(
            "BIBLIOTECA · 500 músicas · página 20/20",
            30,
        )
        controles = player.formatar_controles(
            True,
            lista_visivel=True,
            largura=30,
        )

        self.assertEqual(player.largura_visual(borda), 30)
        self.assertLessEqual(player.largura_visual(controles), 30)


class TestModoAleatorio(unittest.TestCase):
    def test_script_sorteia_indice_diferente_para_n_e_b(self):
        script = player.SCRIPT_NAVEGACAO

        self.assertIn('get_property_native("shuffle", false)', script)
        self.assertIn("math.random(0, total - 2)", script)
        self.assertIn("if destino >= atual then", script)
        self.assertIn('set_property_number("playlist-pos", destino)', script)
        self.assertIn('add_forced_key_binding("n"', script)
        self.assertIn('add_forced_key_binding("b"', script)

    def test_script_mantem_navegacao_sequencial_com_aleatorio_desligado(self):
        script = player.SCRIPT_NAVEGACAO

        self.assertIn("if not mp.get_property_native", script)
        self.assertIn("mp.commandv(comando_sequencial)", script)
        self.assertIn('navegar("playlist-next")', script)
        self.assertIn('navegar("playlist-prev")', script)


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
                caminho_script = next(
                    item.split("=", 1)[1]
                    for item in comando
                    if item.startswith("--script=")
                )
                caminho_playlist = next(
                    item.split("=", 1)[1]
                    for item in comando
                    if item.startswith("--playlist=")
                )
                chamada["socket"] = caminho_socket
                chamada["atalhos"] = Path(caminho_config).read_text()
                chamada["script"] = Path(caminho_script).read_text()
                chamada["playlist"] = Path(caminho_playlist).read_text()
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
        prefixo_pedido = caminho_socket.removesuffix(".sock")
        caminhos_pedidos = {
            "lista": f"{prefixo_pedido}-listar",
            "pagina_anterior": f"{prefixo_pedido}-pagina-anterior",
            "proxima_pagina": f"{prefixo_pedido}-proxima-pagina",
        }
        self.assertEqual(codigo_saida, 0)
        self.assertEqual(comando[0], "mpv")
        self.assertIn("--no-video", comando)
        self.assertIn("--audio-display=no", comando)
        self.assertIn("--loop-playlist=inf", comando)
        self.assertIn("--playlist-start=1", comando)
        self.assertTrue(any(item.startswith("--script=") for item in comando))
        self.assertTrue(comando[-1].startswith("--playlist="))
        self.assertEqual(
            chamada["playlist"].splitlines(),
            [
                "#EXTM3U",
                str(biblioteca / "primeira.mp3"),
                str(biblioteca / "segunda.flac"),
            ],
        )
        self.assertEqual(
            chamada["atalhos"].splitlines(),
            [
                "p cycle pause",
                "P cycle pause",
                "s cycle shuffle",
                "S cycle shuffle",
                f'l run "/usr/bin/touch" "{caminhos_pedidos["lista"]}"',
                f'L run "/usr/bin/touch" "{caminhos_pedidos["lista"]}"',
                (
                    f'PGUP run "/usr/bin/touch" '
                    f'"{caminhos_pedidos["pagina_anterior"]}"'
                ),
                (
                    f'PGDWN run "/usr/bin/touch" '
                    f'"{caminhos_pedidos["proxima_pagina"]}"'
                ),
                "q quit",
                "Q quit",
            ],
        )
        self.assertEqual(chamada["script"], player.SCRIPT_NAVEGACAO)
        exibir_reproducao.assert_called_once_with(
            caminho_socket,
            ["primeira.mp3", "segunda.flac"],
            processo,
            caminhos_pedidos,
        )
        processo.wait.assert_called_once_with(timeout=1)


if __name__ == "__main__":
    unittest.main()
