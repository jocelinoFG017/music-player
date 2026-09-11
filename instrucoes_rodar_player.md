# Instalar e executar no Linux e no Windows

Este guia mostra como instalar os comandos do projeto e executá-los fora da
pasta do repositório:

```text
music-player
music-download
music-update
```

O projeto requer Python 3.10 ou mais recente. O `mpv` é usado para reprodução e
o `ffmpeg` para conversão dos downloads. O `yt-dlp` já está incluído em
`.tools/yt-dlp` e não precisa ser instalado separadamente.

A instalação deve ser feita em modo editável. Dessa forma, os comandos continuam
ligados a esta pasta e encontram `music`, `download-direto` e `.tools/yt-dlp`.

## Linux

### 1. Instalar os programas necessários

No Ubuntu ou Debian, execute:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv mpv ffmpeg
```

Confirme as instalações:

```bash
python3 --version
mpv --version
ffmpeg -version
```

### 2. Criar um ambiente virtual

Entre na pasta do projeto e crie o ambiente:

```bash
cd "/caminho/completo/music-player"
python3 -m venv .venv
source .venv/bin/activate
```

Substitua `/caminho/completo/music-player` pelo caminho real do projeto. Quando
o ambiente estiver ativo, o terminal normalmente mostrará `(.venv)` antes do
comando.

### 3. Instalar os comandos

Com o ambiente ativado, execute:

```bash
python -m pip install --editable .
```

Agora os comandos podem ser usados enquanto o ambiente estiver ativo:

```bash
music-player
music-download "https://www.youtube.com/watch?v=ID_DO_VIDEO"
```

Em um terminal novo, volte ao projeto e reative o ambiente:

```bash
cd "/caminho/completo/music-player"
source .venv/bin/activate
```

### Instalação no usuário, sem ativar o ambiente

Como alternativa, é possível instalar os comandos para o usuário atual:

```bash
python3 -m pip install --user --editable .
```

Se a distribuição bloquear instalações no Python do sistema, use o ambiente
virtual descrito anteriormente. Se a instalação funcionar, mas o terminal não
encontrar os comandos, descubra o diretório-base com:

```bash
python3 -m site --user-base
```

Os executáveis ficam no subdiretório `bin` desse caminho, normalmente
`~/.local/bin`, que precisa fazer parte da variável `PATH`.

## Windows

### Opção recomendada: WSL

O monitoramento da reprodução usa o IPC do `mpv`. No Linux ele é fornecido por
um socket Unix, enquanto o `mpv` usa named pipes no Windows. A implementação
atual do player atende ao formato Unix; por isso, para usar todas as funções no
Windows, a opção recomendada é executar o projeto dentro do WSL.

No PowerShell aberto como administrador, instale o WSL com:

```powershell
wsl --install
```

Reinicie o computador se solicitado, abra a distribuição Ubuntu e siga as
instruções da seção **Linux** deste guia. Mais detalhes estão na
[documentação oficial do WSL](https://learn.microsoft.com/windows/wsl/install).

### Windows nativo: downloader

O downloader pode ser usado diretamente no PowerShell. Instale:

- [Python 3.10 ou mais recente](https://www.python.org/downloads/windows/);
- [ffmpeg para Windows](https://ffmpeg.org/download.html).

Adicione o diretório do `ffmpeg.exe` à variável `PATH`. Depois abra um novo
PowerShell e confirme:

```powershell
py --version
ffmpeg -version
```

Entre na pasta do projeto e crie um ambiente virtual:

```powershell
cd "C:\caminho\completo\music-player"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --editable .
```

Baixe um áudio com:

```powershell
music-download "https://www.youtube.com/watch?v=ID_DO_VIDEO"
```

Se o PowerShell impedir a ativação do ambiente, use o Prompt de Comando na
pasta do projeto:

```bat
.venv\Scripts\activate.bat
music-download "https://www.youtube.com/watch?v=ID_DO_VIDEO"
```

O `mpv` oferece versões para Windows, mas o comando `music-player` ainda não é
suportado nativamente por este projeto devido à diferença de IPC descrita
acima. Consulte a [página oficial de instalação do mpv](https://mpv.io/installation/)
e o [manual de IPC](https://mpv.io/manual/stable/#options-input-ipc-server) para
mais informações.

## Uso sem instalar os comandos

Na pasta do projeto, os programas também podem ser iniciados diretamente.

No Linux ou WSL:

```bash
python3 player.py
python3 downloader.py "LINK"
```

No Windows nativo, para o downloader:

```powershell
py downloader.py "LINK"
```

## Atualizar ou remover a instalação

Como a instalação é editável, alterações no código ficam disponíveis sem
reinstalar. Se a pasta do projeto for movida, execute novamente:

```bash
python -m pip install --editable .
```

Para atualizar com segurança a cópia local do `yt-dlp`, execute:

```bash
music-update
```

Para remover os comandos do ambiente ativo:

```bash
python -m pip uninstall music-player-cli
```

Os arquivos de música e os downloads permanecem nas respectivas pastas do
projeto.
