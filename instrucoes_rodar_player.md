# Como criar o comando `rodar player`

Este guia mostra como configurar o Bash para iniciar o player com um comando
curto, independentemente do nome do usuário ou do local onde o projeto foi
salvo.

Depois da configuração, será possível executar:

```bash
rodar player
```

## 1. Descobrir o caminho do projeto

Abra o terminal, entre na pasta do projeto e execute:

```bash
pwd
```

O terminal mostrará o caminho completo da pasta. Por exemplo:

```text
/home/seu-usuario/projetos/music-player
```

Neste guia, o texto `/caminho/completo/music-player` representa esse caminho.
Substitua-o pelo resultado do comando `pwd` sempre que ele aparecer.

Confirme se o player funciona executando:

```bash
python3 "/caminho/completo/music-player/player.py"
```

Se o player abrir normalmente, continue para a configuração do atalho.

## 2. Abrir a configuração do Bash

Abra o arquivo `.bashrc` com um editor de texto. Usando o Nano, o comando é:

```bash
nano ~/.bashrc
```

O símbolo `~` representa a pasta pessoal do usuário atual. Vá até o final do
arquivo para adicionar a nova função.

## 3. Criar a função `rodar`

Adicione o código abaixo ao final do `.bashrc`:

```bash
rodar() {
    if [ "$1" = "player" ]; then
        python3 "/caminho/completo/music-player/player.py"
    else
        echo "Uso: rodar player"
    fi
}
```

Troque `/caminho/completo/music-player` pelo caminho obtido na primeira etapa.
Mantenha as aspas: elas permitem que o comando funcione mesmo quando alguma
pasta do caminho contém espaços.

A função verifica se a palavra informada depois de `rodar` é `player` e, nesse
caso, executa o arquivo `player.py`.

## 4. Salvar e aplicar a configuração

No Nano, pressione as teclas abaixo:

```text
Ctrl + O
Enter
Ctrl + X
```

Em seguida, recarregue a configuração do Bash:

```bash
source ~/.bashrc
```

Isso torna o novo comando disponível no terminal atual. Nos próximos terminais,
ele será carregado automaticamente.

## 5. Executar o player

Agora, em qualquer pasta, execute:

```bash
rodar player
```

Se `rodar` for executado sem `player`, ou com outro argumento, será exibida a
mensagem:

```text
Uso: rodar player
```

## Observação sobre outros shells

Estas instruções são para o Bash. Para saber qual shell está em uso, execute:

```bash
echo "$SHELL"
```

Se o resultado terminar em `zsh`, adicione a mesma função ao arquivo `~/.zshrc`
e aplique-a com `source ~/.zshrc`. Outros shells podem usar arquivos e sintaxes
diferentes.

## Adicionar mais comandos no futuro

A função pode ser ampliada usando `case`. Por exemplo:

```bash
rodar() {
    case "$1" in
        player)
            python3 "/caminho/completo/music-player/player.py"
            ;;
        servidor)
            echo "Iniciando servidor..."
            ;;
        *)
            echo "Uso:"
            echo "  rodar player"
            echo "  rodar servidor"
            ;;
    esac
}
```

Lembre-se de substituir o caminho do exemplo e recarregar o arquivo de
configuração depois de cada alteração.
