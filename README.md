# Music Player

[![Qualidade](https://github.com/jocelinoFG017/music-player/actions/workflows/ci.yml/badge.svg)](https://github.com/jocelinoFG017/music-player/actions/workflows/ci.yml)

Este projeto possui dois programas:

- `player.py`: reproduz os arquivos de áudio da pasta `music`.
- `downloader.py`: baixa o áudio de um vídeo do YouTube em MP3 e salva na
  pasta `download-direto`.

## Requisitos

- Python 3.10 ou mais recente (a versão recomendada e fixada em
  `.python-version` é a 3.14.7)
- `mpv`, para reproduzir as músicas
- `ffmpeg`, para converter os downloads para MP3

No Ubuntu, instale os programas necessários com:

```bash
sudo apt install mpv ffmpeg
```

Confira se o interpretador ativo é o esperado:

```bash
python3 --version
```

Gerenciadores como `pyenv`, `mise` e `asdf` reconhecem o arquivo
`.python-version` e selecionam automaticamente o Python 3.14.7 quando essa
versão está instalada. Ela é a versão recomendada para desenvolvimento, mas o
projeto aceita qualquer Python a partir do 3.10, conforme declarado em
`pyproject.toml`.

Não é necessário instalar `yt-dlp` pelo Ubuntu ou pelo `pip`. O projeto usa
sua própria cópia atualizada, localizada em `.tools/yt-dlp`, evitando conflitos
com versões antigas instaladas no sistema.

## Instalar os comandos

Consulte o [guia de instalação para Linux e Windows](instrucoes_rodar_player.md)
para um passo a passo completo.

Na pasta do projeto, faça a instalação editável usando o ambiente Python em que
os comandos devem ficar disponíveis:

```bash
python3 -m pip install --editable .
```

A instalação editável mantém os comandos ligados a esta pasta, permitindo que
eles encontrem a biblioteca `music` e a cópia local do `yt-dlp`. Depois disso,
o player pode ser iniciado de qualquer diretório com:

```bash
music-player
```

Para baixar um áudio, execute:

```bash
music-download "https://www.youtube.com/watch?v=ID_DO_VIDEO"
```

Se a pasta do projeto for movida, execute novamente a instalação editável no
novo local. Os comandos antigos podem ser removidos com:

```bash
python3 -m pip uninstall music-player-cli
```

## Reproduzir músicas

Coloque seus arquivos de áudio dentro da pasta `music` e execute o comando
instalado:

```bash
music-player
```

Sem instalar o comando, também é possível usar `python3 player.py` a partir da
pasta do projeto.

Formatos aceitos: MP3, WAV, OGG, FLAC e M4A.

Ao iniciar, o player toca imediatamente a primeira música da biblioteca em
ordem alfabética, sem exibir uma tela de seleção.

Os arquivos colocados em `music` são locais e não são versionados pelo Git.
A pasta é mantida no projeto por meio do arquivo `music/.gitkeep`.

Durante a reprodução:

- `[P]`: pausar ou continuar
- `[N]`: próxima música
- `[B]`: música anterior
- `[S]`: ativar ou desativar o modo aleatório, reorganizando a fila
- `[L]`: listar as músicas; pressione novamente para voltar à reprodução
- `[Q]`: sair da reprodução

Ao terminar a última música, a reprodução volta automaticamente para a
primeira. Ao abrir a lista com `[L]`, a música atual é indicada pelo marcador
`>`. Com o modo aleatório ligado, `[N]` avança pela ordem embaralhada e `[B]`
volta pelo mesmo histórico. Ao sair, o comando é encerrado.

Se o `mpv` não estiver instalado, não puder ser iniciado ou encerrar com erro,
o player informa o problema no terminal e termina com um código de saída de
erro, sem deixar arquivos temporários ou processos de reprodução abertos.

## Baixar áudio do YouTube

Execute o comando instalado e cole o link quando solicitado:

```bash
music-download
```

Também é possível passar o link diretamente no comando:

```bash
music-download "https://www.youtube.com/watch?v=ID_DO_VIDEO"
```

Sem instalar o comando, as formas equivalentes são `python3 downloader.py` e
`python3 downloader.py "LINK"` a partir da pasta do projeto.

O programa aceita links `youtube.com` e `youtu.be`, seleciona o áudio de melhor
qualidade disponível e o converte para MP3. Os arquivos são salvos na pasta
`download-direto`, com o título e o identificador do vídeo no nome.

Os áudios dessa pasta também são locais e não são versionados pelo Git. Apenas
o arquivo `download-direto/.gitkeep`, usado para manter a pasta no projeto, é
versionado.

Se o link também fizer parte de uma playlist, somente o vídeo indicado será
baixado.

## Atualizar o yt-dlp local

Se o YouTube mudar e o downloader deixar de extrair os vídeos, atualize somente
a cópia armazenada dentro deste projeto com:

```bash
music-update
```

Sem instalar os comandos do projeto, use:

```bash
python3 atualizar_ytdlp.py
```

O atualizador baixa o executável e a lista oficial de checksums em uma pasta
temporária, confere o SHA-256 e executa a nova cópia com `--version`. A troca é
atômica e acontece somente depois dessas validações; em caso de erro, o arquivo
anterior é preservado.

O `downloader.py` não utiliza o `yt-dlp` antigo fornecido pelo Ubuntu. Todos os
downloads e a ferramenta atualizada permanecem dentro da pasta do projeto.

Use o downloader apenas para conteúdos que você tem autorização para baixar.

## Executar os testes

Os testes usam apenas a biblioteca padrão do Python e não reproduzem áudio nem
fazem downloads. Execute a suíte completa com:

```bash
python3 -m unittest discover -s tests -v
```

O GitHub Actions executa a verificação de sintaxe e os testes no Python 3.10 e
3.14 a cada `push` e `pull request`. A cópia local do `yt-dlp` também é comparada
com a versão estável mais recente e recebe uma verificação semanal automática.
