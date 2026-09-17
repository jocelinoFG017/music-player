# Music Player

[![Qualidade](https://github.com/jocelinoFG017/music-player/actions/workflows/ci.yml/badge.svg)](https://github.com/jocelinoFG017/music-player/actions/workflows/ci.yml)

Um player de músicas simples para o terminal, com uma ferramenta adicional para
baixar áudios do YouTube.

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

### Estatísticas

O player registra localmente o tempo efetivamente ouvido. Pausas não entram no
tempo e uma faixa só conta como reprodução depois de 50% da duração ou 4
minutos, o que ocorrer primeiro. Os dados ficam em `stats.json`, fora da pasta
de músicas.

```bash
rodar player stats
rodar player stats today
rodar player stats week
rodar player stats month
rodar player stats year
rodar player stats all
```

`all-time` também é aceito como sinônimo de `all`.

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

```bash
python3 downloader.py "LINK_DO_YOUTUBE"
```

O arquivo MP3 será salvo em `download-direto`. Para ouvi-lo no player, mova-o
para a pasta `music`.

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
