import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from music_player_core import library


class TestConfiguracaoCompartilhada(unittest.TestCase):
    def test_salva_pasta_de_download_preservando_biblioteca(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "config.json"
            caminho.write_text(
                json.dumps({"library_path": "/musicas"}),
                encoding="utf-8",
            )

            with patch.object(library, "CAMINHO_CONFIGURACAO", caminho):
                library.salvar_configuracao(download_path="/downloads")
                configuracao = library.carregar_configuracao()

        self.assertEqual(configuracao["library_path"], "/musicas")
        self.assertEqual(configuracao["download_path"], "/downloads")


if __name__ == "__main__":
    unittest.main()
