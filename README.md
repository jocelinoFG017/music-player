# Music Player

[![Qualidade](https://github.com/jocelinoFG017/music-player/actions/workflows/ci.yml/badge.svg)](https://github.com/jocelinoFG017/music-player/actions/workflows/ci.yml)

Um player de músicas simples para o terminal, com uma ferramenta adicional para
baixar áudios do YouTube. O projeto também possui um player gráfico independente
que compartilha a biblioteca e o histórico com o terminal.

## ▶️ Rodar o player

1. Coloque suas músicas na pasta `music`.
2. No Ubuntu em que o atalho do projeto já foi configurado, execute:

```bash
rodar player
```

Em outro computador Linux, entre na pasta do projeto e use:

```bash
python3 player.py
```

Formatos aceitos: MP3, WAV, OGG, FLAC e M4A.
Também são encontradas músicas organizadas em subpastas de `music`.

## 🖥️ Rodar o player gráfico

O GUI é um MVP independente feito com Qt/PySide6, com biblioteca, reprodução,
pausa e avanço de faixa. Ele usa a mesma pasta de músicas e o mesmo banco de
estatísticas do CLI. Na primeira vez, crie o ambiente e instale o projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Depois, abra o GUI:

```bash
music-player-gui
```

Também é possível executá-lo diretamente dentro do ambiente virtual:

```bash
python3 gui.py
```

### Estatísticas

O player registra localmente o tempo efetivamente ouvido. Pausas não entram no
tempo e uma faixa só conta como reprodução depois de 50% da duração ou 4
minutos, o que ocorrer primeiro. CLI e GUI gravam no mesmo banco SQLite, por
padrão em `~/.local/share/music-player/stats.db`.

```bash
rodar player stats
rodar player stats today
rodar player stats week
rodar player stats month
rodar player stats year
rodar player stats all
```

`all-time` também é aceito como sinônimo de `all`.

Na primeira execução, o histórico existente em `stats.json` é importado
automaticamente e preservado em um backup. Veja
[MIGRACAO_SQLITE.md](MIGRACAO_SQLITE.md) para detalhes e opções de configuração.

### Imagens

![Play](assets/play.png)

![List](assets/list.png)

### Controles

| Tecla | Ação |
|---|---|
| `P` | Pausar ou continuar |
| `N` | Próxima música |
| `B` | Música anterior |
| `S` | Ativar ou desativar o modo aleatório |
| `R` | Repetir a música atual |
| `A` | Atualizar a biblioteca com novas músicas |
| `L` | Mostrar ou fechar a lista de músicas |
| `PgUp` / `PgDn` | Navegar pela lista |
| `Q` | Sair |

## ⬇️ Baixar uma música

Na aba **Downloader** do GUI, cole o link, escolha a pasta de destino e clique
em **Baixar MP3**. A pasta escolhida fica salva para os próximos downloads.

Pelo terminal, `download-direto` continua sendo o destino padrão:

```bash
python3 downloader.py "LINK_DO_YOUTUBE"
```

Também é possível escolher o destino no comando:

```bash
python3 downloader.py "LINK_DO_YOUTUBE" --output-dir "/pasta/escolhida"
```

Se uma pasta tiver sido escolhida anteriormente no GUI, ela também passa a ser
o destino padrão do downloader no terminal. Para ouvir o arquivo no player,
mova-o para a biblioteca configurada.

Use o downloader apenas para conteúdos que você tem autorização para baixar.

## 🔄 Atualizar o downloader

Se o download parar de funcionar por causa de uma mudança no YouTube, execute:

```bash
python3 atualizar_ytdlp.py
```

## Primeira instalação

Veja o guia curto para [instalar e rodar no Ubuntu ou Windows](instrucoes_rodar_player.md).

## Testes

```bash
python3 -m unittest discover -s tests -v
```
