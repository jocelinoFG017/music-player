# Como instalar e rodar o player

## 🐧 Ubuntu

### 1. Instale o necessário

```bash
sudo apt update
sudo apt install python3 mpv ffmpeg
```

### 2. Adicione suas músicas

Coloque os arquivos MP3, WAV, OGG, FLAC ou M4A dentro da pasta `music`.

### 3. Rode o player

Neste Ubuntu, o atalho do projeto já está configurado. Ele funciona em qualquer
pasta do terminal:

```bash
rodar player
```

Se o terminal ainda não reconhecer o atalho, abra um terminal novo ou execute:

```bash
source ~/.bashrc
```

Sem o atalho, entre na pasta do projeto e rode diretamente:

```bash
python3 player.py
```

Pronto. O player começa pela primeira música da pasta `music`.

<details>
<summary>Configurar o atalho em outro Ubuntu</summary>

Abra o arquivo de configuração do terminal:

```bash
nano ~/.bashrc
```

Adicione ao final do arquivo, trocando o caminho pelo local do projeto:

```bash
rodar() {
    if [ "$1" = "player" ]; then
        python3 "/caminho/completo/music-player/player.py" "${@:2}"
    else
        echo "Uso: rodar player [stats [today|week|month|year|all]]"
    fi
}
```

Salve e carregue o atalho:

```bash
source ~/.bashrc
```

</details>

## 🪟 Windows

O player precisa do Linux para oferecer todos os controles. No Windows, use o
WSL (Ubuntu):

1. Abra o PowerShell como administrador.
2. Execute `wsl --install`.
3. Reinicie o computador, caso seja solicitado.
4. Abra o Ubuntu e siga os passos da seção **Ubuntu** acima.

## ⬇️ Baixar áudio

No Ubuntu ou WSL, dentro da pasta do projeto:

```bash
python3 downloader.py "LINK_DO_YOUTUBE"
```

O MP3 fica em `download-direto`. Mova o arquivo para `music` se quiser ouvi-lo
no player.
