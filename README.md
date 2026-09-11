# Music Player

Este projeto possui dois programas:

- `player.py`: reproduz os arquivos de áudio da pasta `music`.
- `downloader.py`: baixa o áudio de um vídeo do YouTube em MP3 e salva na
  pasta `download-direto`.

## Requisitos

- Python 3.14 (a versão recomendada e fixada em `.python-version` é a 3.14.7)
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
versão está instalada. O intervalo suportado pelo projeto também está declarado
em `pyproject.toml`.

Não é necessário instalar `yt-dlp` pelo Ubuntu ou pelo `pip`. O projeto usa
sua própria cópia atualizada, localizada em `.tools/yt-dlp`, evitando conflitos
com versões antigas instaladas no sistema.

## Reproduzir músicas

Coloque seus arquivos de áudio dentro da pasta `music` e execute:

```bash
python3 player.py
```

Formatos aceitos: MP3, WAV, OGG, FLAC e M4A.

Os arquivos colocados em `music` são locais e não são versionados pelo Git.
A pasta é mantida no projeto por meio do arquivo `music/.gitkeep`.

Durante a reprodução:

- `[P]`: pausar ou continuar
- `[N]`: próxima música
- `[B]`: música anterior
- `[S]`: ativar ou desativar o modo aleatório
- `[Q]`: sair da reprodução

Ao terminar a última música, a reprodução volta automaticamente para a
primeira. Ao sair, a tela é limpa antes de retornar à seleção de músicas.

Se o `mpv` não estiver instalado, não puder ser iniciado ou encerrar com erro,
o player informa o problema no terminal e termina com um código de saída de
erro, sem deixar arquivos temporários ou processos de reprodução abertos.

## Baixar áudio do YouTube

Execute o downloader e cole o link quando solicitado:

```bash
python3 downloader.py
```

Também é possível passar o link diretamente no comando:

```bash
python3 downloader.py "https://www.youtube.com/watch?v=ID_DO_VIDEO"
```

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
a cópia armazenada dentro deste projeto:

```bash
curl --fail --location \
  --output .tools/yt-dlp.novo \
  https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
mv .tools/yt-dlp.novo .tools/yt-dlp
```

Confira a versão local com:

```bash
python3 .tools/yt-dlp --version
```

O `downloader.py` não utiliza o `yt-dlp` antigo fornecido pelo Ubuntu. Todos os
downloads e a ferramenta atualizada permanecem dentro da pasta do projeto.

Use o downloader apenas para conteúdos que você tem autorização para baixar.
