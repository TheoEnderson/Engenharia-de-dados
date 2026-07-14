# Parte 2 — MongoDB e CRUD local

Esta pasta contém o mapeamento das 16 tabelas do schema `universidade` e uma
aplicação Flask independente para o CRUD de `usuario`, `estudante`, `vinculo` e
`curso`. Nesta etapa, a aplicação funciona exclusivamente com `mongomock`, em
memória, sem acessar o Atlas.

## Segurança

- Credenciais não ficam no código.
- `.env` é ignorado pelo Git e não é necessário para dry-run.
- Sem `MONGODB_MODE=mock`, a aplicação web não inicia e nunca tenta Atlas.
- `ETL.py` e `setup_banco.py` não conectam ao MongoDB quando importados.
- Os dois scripts usam dry-run por padrão.
- Operações remotas exigem `--apply` e as variáveis `MONGODB_URI` e
  `MONGODB_DATABASE`.
- O setup não remove duplicatas e não insere exemplos.
- O ETL nunca exclui documentos; no modo apply futuro, usa upsert por chave
  primária.

O arquivo `.env.example` contém somente os nomes das variáveis. Não coloque
credenciais reais no repositório.

## Aplicação CRUD local

Instale as dependências no ambiente virtual e inicie explicitamente em mock:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
MONGODB_MODE=mock ./.venv/bin/flask --app app run --debug
```

O terminal mostrará `[MODO MOCK]`. O banco é temporário e volta vazio a cada
reinício. Um conjunto mínimo de demonstração só é criado quando a flag também é
explícita:

```bash
MONGODB_MODE=mock DEMO_SEED=1 ./.venv/bin/flask --app app run --debug
```

Rotas principais:

- `/usuarios`, `/usuarios/novo` e fichas/edições por CPF;
- `/estudantes`, `/estudantes/novo` e fichas/edições por matrícula;
- `/vinculos`, `/vinculos/novo` e fichas/edições pelo ID interno;
- `/cursos`, `/cursos/novo` e fichas/edições pelo ID interno;
- `/admissoes/nova`, fluxo atômico de usuário, estudante e vínculo inicial.

As senhas permanecem no campo definido pelo schema/dump para preservar a
decisão de modelagem atual, mas nunca são devolvidas pelos serviços nem exibidas
em HTML. Alterar para hash exigirá uma decisão explícita sobre o limite SQL de
32 caracteres e uma migração do schema.

## Uso offline

```bash
python3 setup_banco.py --dry-run
python3 ETL.py --input universidade-dump-engdados.sql --dry-run
./.venv/bin/python -m unittest discover -s tests -v
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
- `repositories.py`: acesso MongoDB injetável e rollback mock.
- `services.py`: validações e integridade dos quatro CRUDs.
- `app.py`, `templates/` e `static/`: aplicação Flask responsiva.
- `tests/`: testes exclusivamente offline.

Ainda faltam homologação contra um ambiente Atlas autorizado, transações reais,
evidências da apresentação e decisões finais de segurança. Este projeto não
representa a conclusão da Parte 2.
