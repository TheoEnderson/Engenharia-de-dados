# Parte 2 — Fundação MongoDB offline

Esta pasta contém a fundação segura do mapeamento relacional para MongoDB. As
16 tabelas do schema `universidade` são representadas por coleções próprias.
Ainda não há interface web ou CRUD visual.

## Segurança

- Credenciais não ficam no código.
- `.env` é ignorado pelo Git e não é necessário para dry-run.
- `ETL.py` e `setup_banco.py` não conectam ao MongoDB quando importados.
- Os dois scripts usam dry-run por padrão.
- Operações remotas exigem `--apply` e as variáveis `MONGODB_URI` e
  `MONGODB_DATABASE`.
- O setup não remove duplicatas e não insere exemplos.
- O ETL nunca exclui documentos; no modo apply futuro, usa upsert por chave
  primária.

O arquivo `.env.example` contém somente os nomes das variáveis. Não coloque
credenciais reais no repositório.

## Uso offline

```bash
python3 setup_banco.py --dry-run
python3 ETL.py --input universidade-dump-engdados.sql --dry-run
python3 -m unittest discover -s tests -v
```

As flags `--dry-run` são opcionais porque esse é o comportamento padrão.

## Operações remotas futuras

Somente depois de autorização, backup e revisão do dry-run:

```bash
python3 setup_banco.py --apply
python3 ETL.py --input universidade-dump-engdados.sql --apply
```

Esses comandos não devem ser executados contra produção sem preflight de dados
existentes. Índices únicos podem falhar se o banco remoto já tiver duplicatas;
nenhum script as remove automaticamente.

## Estrutura

- `config.py`: configuração local e variáveis de ambiente.
- `db.py`: criação tardia do cliente MongoDB.
- `schemas_mongodb.py`: validators, índices, chaves e referências.
- `setup_banco.py`: planejamento/aplicação explícita de schema.
- `ETL.py`: parser, validação referencial, relatório e upserts futuros.
- `docs/mapeamento-nosql.md`: projeto lógico e restrições.
- `tests/`: testes exclusivamente offline.

O CRUD completo de `usuario`, `estudante`, `vinculo` e `curso` pertence à
próxima etapa. Esta fundação não representa a conclusão da Parte 2.
