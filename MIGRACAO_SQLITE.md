# Migração das estatísticas para SQLite

O player passou a usar SQLite para que o CLI e o GUI possam registrar sessões
no mesmo histórico com segurança. O SQLite é local e não requer servidor.

## Local dos dados

Por padrão, o banco é criado em:

```text
~/.local/share/music-player/stats.db
```

Se `XDG_DATA_HOME` estiver definido, o banco fica em
`$XDG_DATA_HOME/music-player/stats.db`. Para escolher outro diretório, defina:

```bash
export MUSIC_PLAYER_DATA_DIR="/caminho/para/os/dados"
```

CLI e GUI precisam enxergar o mesmo valor dessa configuração para compartilhar
o histórico.

## Importação do `stats.json`

Na primeira leitura ou gravação do banco, o sistema procura o `stats.json` na
raiz deste projeto. Quando ele existe:

1. cria as tabelas do SQLite;
2. copia o JSON para `stats-v1.backup.json` no diretório de dados;
3. importa cada sessão e seus tempos por dia em uma única transação;
4. marca a migração no próprio banco para que ela não seja repetida.

O `stats.json` original não é apagado nem alterado. Se a importação falhar, a
transação é revertida e o histórico original continua disponível.

As sessões antigas mantêm os registros por dia e os horários de início, fim e
contabilização já existentes. As novas sessões também registram o tempo ouvido
por hora, preparando consultas e gráficos futuros.

## Biblioteca compartilhada

Os dois players usam `music/` como biblioteca padrão. É possível configurar uma
biblioteca comum temporariamente:

```bash
export MUSIC_PLAYER_LIBRARY="/caminho/para/minhas-musicas"
```

Para uma configuração persistente, crie
`~/.config/music-player/config.json`:

```json
{
  "library_path": "/caminho/para/minhas-musicas"
}
```

Se `XDG_CONFIG_HOME` estiver definido, o arquivo de configuração fica em
`$XDG_CONFIG_HOME/music-player/config.json`. O diretório também pode ser
alterado com `MUSIC_PLAYER_CONFIG_DIR`.

## Concorrência

O banco usa o modo WAL e espera brevemente por escritas concorrentes. Dessa
forma, o GUI e o CLI podem acessar o histórico ao mesmo tempo sem reescrever o
arquivo inteiro a cada atualização.
