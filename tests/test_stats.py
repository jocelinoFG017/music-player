import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path

import stats


class TestPersistencia(unittest.TestCase):
    def test_primeira_execucao_sem_arquivo(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "stats.json"

            dados = stats.carregar(str(caminho))

        self.assertEqual(dados, {"version": 1, "sessions": []})

    def test_gravacao_atomica_e_atualizacao_da_mesma_sessao(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "stats.json"
            sessao = {
                "id": "sessao-1",
                "track": "music/faixa.mp3",
                "folder": "music/",
                "listened_seconds": 5,
            }
            stats.salvar_sessao(sessao, str(caminho))
            sessao["listened_seconds"] = 10
            stats.salvar_sessao(sessao, str(caminho))

            dados = stats.carregar(str(caminho))

        self.assertEqual(len(dados["sessions"]), 1)
        self.assertEqual(dados["sessions"][0]["listened_seconds"], 10)


class TestRastreamento(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.caminho = str(Path(self.diretorio.name) / "stats.json")
        self.inicio = datetime(2026, 9, 14, 10, tzinfo=timezone.utc)

    def tearDown(self):
        self.diretorio.cleanup()

    def atualizar(self, rastreador, musica, posicao, monotonic, pausada=False):
        rastreador.atualizar(
            musica,
            posicao,
            120,
            pausada,
            instante_monotonic=monotonic,
            agora=self.inicio,
        )

    def test_pausa_nao_conta_e_tempo_ouvido_e_salvo_ao_fechar(self):
        rastreador = stats.RastreadorReproducao(self.caminho)
        self.atualizar(rastreador, "faixa.mp3", 0, 0)
        self.atualizar(rastreador, "faixa.mp3", 10, 10)
        self.atualizar(rastreador, "faixa.mp3", 11, 11, pausada=True)
        self.atualizar(rastreador, "faixa.mp3", 11, 31, pausada=True)
        self.atualizar(rastreador, "faixa.mp3", 11, 32)
        self.atualizar(rastreador, "faixa.mp3", 21, 42)
        rastreador.finalizar(agora=self.inicio)

        sessao = stats.carregar(self.caminho)["sessions"][0]
        self.assertAlmostEqual(sessao["listened_seconds"], 21)
        self.assertFalse(sessao["counted_play"])

    def test_pulo_rapido_nao_conta_reproducao_e_troca_cria_sessao(self):
        rastreador = stats.RastreadorReproducao(self.caminho)
        self.atualizar(rastreador, "primeira.mp3", 0, 0)
        self.atualizar(rastreador, "primeira.mp3", 5, 5)
        self.atualizar(rastreador, "rock/segunda.mp3", 0, 6)
        self.atualizar(rastreador, "rock/segunda.mp3", 65, 71)
        rastreador.finalizar(agora=self.inicio)

        sessoes = stats.carregar(self.caminho)["sessions"]
        self.assertEqual(len(sessoes), 2)
        self.assertFalse(sessoes[0]["counted_play"])
        self.assertTrue(sessoes[1]["counted_play"])
        self.assertEqual(sessoes[1]["track"], "music/rock/segunda.mp3")
        self.assertEqual(sessoes[1]["folder"], "rock/")

    def test_reinicio_da_mesma_faixa_registra_nova_reproducao(self):
        rastreador = stats.RastreadorReproducao(self.caminho)
        self.atualizar(rastreador, "faixa.mp3", 0, 0)
        self.atualizar(rastreador, "faixa.mp3", 70, 70)
        self.atualizar(rastreador, "faixa.mp3", 0, 71)
        self.atualizar(rastreador, "faixa.mp3", 70, 141)
        rastreador.finalizar(agora=self.inicio)

        sessoes = stats.carregar(self.caminho)["sessions"]
        self.assertEqual(len(sessoes), 2)
        self.assertTrue(all(sessao["counted_play"] for sessao in sessoes))


class TestPeriodosESaida(unittest.TestCase):
    def setUp(self):
        self.dados = {
            "version": 1,
            "sessions": [
                {
                    "track": "music/rock/igual.mp3",
                    "folder": "rock/",
                    "listened_by_day": {
                        "2026-09-14": 600,
                        "2026-09-01": 300,
                    },
                    "counted_play": True,
                    "counted_at": "2026-09-14T10:00:00-03:00",
                },
                {
                    "track": "music/sertanejo/igual.mp3",
                    "folder": "sertanejo/",
                    "listened_by_day": {"2026-08-01": 120},
                    "counted_play": True,
                    "counted_at": "2026-08-01T10:00:00-03:00",
                },
            ],
        }

    def test_calcula_hoje_sem_perder_historico_all_time(self):
        hoje = date(2026, 9, 14)

        atual = stats.calcular(self.dados, "today", hoje)
        geral = stats.calcular(self.dados, "all", hoje)

        self.assertEqual(atual["listened_seconds"], 600)
        self.assertEqual(atual["plays"], 1)
        self.assertEqual(geral["listened_seconds"], 1020)
        self.assertEqual(geral["plays"], 2)
        self.assertEqual(geral["folder_plays"]["rock/"], 1)

    def test_comando_sem_arquivo_e_filtros_validos(self):
        for periodo in (None, "today", "week", "month", "year", "all"):
            with self.subTest(periodo=periodo):
                with tempfile.TemporaryDirectory() as diretorio:
                    caminho = str(Path(diretorio) / "stats.json")
                    saida = io.StringIO()
                    with redirect_stdout(saida):
                        codigo = stats.executar(periodo, caminho)
                self.assertEqual(codigo, 0)
                self.assertIn("ESTATÍSTICAS", saida.getvalue())

    def test_periodo_invalido_retorna_erro_de_uso(self):
        erro = io.StringIO()
        with redirect_stderr(erro):
            codigo = stats.executar("ontem")

        self.assertEqual(codigo, 2)
        self.assertIn("Uso:", erro.getvalue())


if __name__ == "__main__":
    unittest.main()
