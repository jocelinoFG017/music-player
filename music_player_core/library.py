import json
import os
from pathlib import Path


EXTENSOES_AUDIO = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def _diretorio_configuracao():
    personalizado = os.environ.get("MUSIC_PLAYER_CONFIG_DIR")
    if personalizado:
        return Path(personalizado).expanduser()
    base_xdg = os.environ.get("XDG_CONFIG_HOME")
    if base_xdg:
        return Path(base_xdg).expanduser() / "music-player"
    return Path.home() / ".config" / "music-player"


CAMINHO_CONFIGURACAO = _diretorio_configuracao() / "config.json"


def pasta_musicas():
    """Retorna a biblioteca comum aos dois players.

    A variável de ambiente é útil para uma execução pontual. A configuração
    persistente fica fora do repositório e pode ser usada tanto pelo CLI quanto
    pelo GUI.
    """
    personalizada = os.environ.get("MUSIC_PLAYER_LIBRARY")
    if personalizada:
        return Path(personalizada).expanduser().resolve()

    try:
        with CAMINHO_CONFIGURACAO.open(encoding="utf-8") as arquivo:
            configuracao = json.load(arquivo)
        configurada = configuracao.get("library_path")
        if configurada:
            return Path(configurada).expanduser().resolve()
    except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError):
        pass

    return RAIZ_PROJETO / "music"


def listar_musicas(diretorio=None):
    diretorio = Path(diretorio or pasta_musicas())
    musicas = []
    for raiz, _, arquivos in os.walk(diretorio):
        raiz = Path(raiz)
        for arquivo in arquivos:
            if arquivo.lower().endswith(EXTENSOES_AUDIO):
                musicas.append((raiz / arquivo).relative_to(diretorio).as_posix())
    return sorted(musicas, key=str.casefold)
