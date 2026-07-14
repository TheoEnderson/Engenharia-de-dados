# Parte 2 — CRUD NoSQL com MongoDB

## 1. Identificação

**Disciplina:** Engenharia de Dados  
**Professor:** André Britto de Carvalho  
**Integrantes:** Allan Gustavo, Pedro Guilherme & Théo Enderson 
**Link do repositório GitHub:** https://github.com/pedroguiao/Engenharia-de-dados

Este relatório documenta o estado atual da Parte 2 do Trabalho Prático de
Engenharia de Dados. As implementações e os testes locais estão disponíveis no
código-fonte do projeto. A implantação e a coleta de evidências no MongoDB Atlas
ainda estão pendentes.

## 2. Objetivo

A Parte 2 tem como objetivo mapear o modelo relacional da universidade para o
MongoDB e disponibilizar uma aplicação capaz de manipular as estruturas NoSQL.
Nesta etapa foram realizados:

- o mapeamento das 16 tabelas relacionais para coleções MongoDB;
- a definição de documentos, validators, índices, chaves e referências;
- o CRUD de `usuario`, `estudante`, `vinculo` e `curso`;
- uma interface Flask para cadastro, consulta, edição e exclusão;
- rotinas seguras de preparação do banco e carga do dump SQL;
- validações e testes automatizados executados em banco MongoDB simulado.

## 3. Tecnologias utilizadas

| Tecnologia | Utilização no projeto |
|---|---|
| Python | Linguagem principal da aplicação, das regras de negócio, do setup, do ETL e dos testes. |
| Flask | Framework web utilizado nas rotas, formulários, fichas, mensagens e interface CRUD. |
| MongoDB | SGBD NoSQL escolhido para representar as estruturas do modelo relacional. |
| PyMongo | Driver preparado para operações futuras com MongoDB real e para tipos BSON, como `Decimal128`. |
| mongomock | Implementação MongoDB em memória usada nos testes e na execução local, sem conexão de rede. |
| HTML e CSS | Construção da interface responsiva, menu lateral, formulários, tabelas e páginas de detalhe. |
| unittest | Framework dos 32 testes automatizados locais. |

## 4. Modelagem MongoDB

Cada tabela relacional foi representada por uma coleção MongoDB própria. As
coleções `usuario`, `estudante`, `vinculo` e `curso` são canônicas e
independentes, o que facilita o CRUD separado e evita cópias divergentes.

Os campos multivalorados `email` e `telefone` são arrays dentro do documento
`usuario`. Os relacionamentos entre coleções são armazenados por CPF, matrícula,
códigos e identificadores. Por exemplo, `estudante.cpf` referencia
`usuario.cpf`, enquanto `vinculo.mat_estudante` e `vinculo.idCurso` referenciam
estudante e curso.

MongoDB não possui foreign keys automáticas. Por esse motivo, o ETL verifica as
referências durante o dry-run, e a camada de serviços verifica a existência de
documentos referenciados antes das operações do CRUD. Exclusões que deixariam
referências órfãs são bloqueadas pela aplicação.

### 4.1 Estruturas mapeadas

| Tabela relacional | Coleção MongoDB | Chave principal | Referências |
|---|---|---|---|
| **usuario** | **usuario** | **`cpf`** | — |
| professor | professor | `mat_professor` | `cpf` → usuario; `departamento` → departamento |
| departamento | departamento | `cod_depto` | `chefe` → professor |
| **curso** | **curso** | **`idCurso`** | — |
| **estudante** | **estudante** | **`mat_estudante`** | **`cpf` → usuario** |
| **vinculo** | **vinculo** | **`idVinculo`** | **`mat_estudante` → estudante; `idCurso` → curso** |
| projeto | projeto | `id_projeto` | — |
| plano | plano | (`mat_estudante`, `ano`) | `id_projeto` → projeto; `mat_professor` → professor; `mat_estudante` → estudante |
| disciplina | disciplina | `cod_disc` | `pre_req` → disciplina; `depto_responsavel` → departamento |
| semestre | semestre | (`ano`, `semestre`) | — |
| sala | sala | `id_sala` | — |
| horario | horario | `id_horario` | — |
| turma | turma | `id_turma` | `cod_disc` → disciplina; (`ano`, `semestre`) → semestre |
| leciona | leciona | (`id_turma`, `mat_professor`) | `id_turma` → turma; `mat_professor` → professor |
| alocacao | alocacao | (`id_turma`, `id_horario`) | `id_turma` → turma; `id_horario` → horario; `id_sala` → sala¹ |
| cursa | cursa | (`mat_estudante`, `id_turma`) | `mat_estudante` → estudante; `id_turma` → turma |

¹ As referências de `alocacao` foram inferidas pelo significado dos campos; o
dump SQL não declara foreign keys nessa tabela.

Além das chaves principais, foram modeladas chaves únicas, chaves compostas,
limites de tamanho, campos obrigatórios, tipos, enums e regras `CHECK`. A
aplicação acrescenta a unicidade de (`mat_estudante`, `idCurso`) em `vinculo`
para impedir vínculo repetido do mesmo estudante com o mesmo curso.

## 5. Arquitetura da aplicação

O projeto separa interface, regras de negócio e persistência:

```text
Interface Flask → Serviços → Repositórios → MongoDB
```

| Componente | Responsabilidade |
|---|---|
| `app.py` | Cria a aplicação Flask, registra rotas, recebe formulários, mostra mensagens e renderiza templates. |
| `services.py` | Implementa validações, unicidade, integridade referencial, bloqueios de exclusão e admissão conjunta. |
| `repositories.py` | Encapsula consultas e escritas MongoDB, impede operadores recebidos como valores e oferece fronteira transacional injetável. |
| `db.py` | Cria o banco em memória com mongomock e mantém separada a criação futura do cliente MongoDB real. |
| `schemas_mongodb.py` | Centraliza validators, índices, chaves principais, chaves únicas e referências das 16 coleções. |
| `setup_banco.py` | Planeja ou aplica coleções, validators e índices; usa dry-run por padrão. |
| `ETL.py` | Lê o dump SQL, converte tipos, cria documentos, verifica duplicidades/referências e prepara upserts. |
| `templates/` | Contém painel, formulários, listagens, fichas, admissão e páginas de erro. |
| `static/` | Contém o CSS responsivo e a identidade visual da aplicação. |
| `tests/` | Contém testes do parser, do mapeamento, dos serviços CRUD e das rotas Flask. |

A aplicação web atual somente inicia quando `MONGODB_MODE=mock`. Nesse modo, o
banco é temporário, não abre conexão de rede e é reiniciado junto com o processo.
Dados de demonstração somente são inseridos quando `DEMO_SEED=1` é informado
explicitamente.

## 6. Preparação do banco

O arquivo `setup_banco.py` possui definições para criar ou atualizar as 16
coleções, aplicar validators e criar índices. O comportamento padrão é dry-run:
sem `--apply`, o script apenas mostra o plano. Ele não remove duplicatas, não
executa seeds e não substitui documentos existentes.

O arquivo `ETL.py` lê `universidade-dump-engdados.sql`, reconhece INSERTs e os
UPDATEs de chefia, converte arrays, datas, inteiros e decimais e produz um
documento para cada registro. Antes de qualquer escrita, o dry-run verifica
campos, duplicidades e referências.

O último dry-run confirmado apresentou:

- **238 registros lidos e válidos**;
- **0 registros inválidos**;
- **0 duplicidades**;
- **0 referências ausentes**;
- **4 UPDATEs de chefia processados em memória**;
- nenhuma inconsistência bloqueante.

Os comandos `setup_banco.py --apply` e `ETL.py --apply` **não foram executados no
MongoDB Atlas**. A preparação remota continua pendente.

## 7. CRUD implementado

### 7.1 Usuario

- **Create:** cadastra CPF, nome, data de nascimento, arrays de e-mail e
  telefone, login e senha.
- **Read:** lista usuários e exibe ficha individual sem retornar a senha.
- **Update:** altera os campos permitidos; CPF é imutável e senha vazia mantém o
  valor anterior.
- **Delete:** exclui o usuário somente quando não existe estudante relacionado.
- CPF e login são verificados quanto à unicidade.
- A senha não é incluída nos retornos públicos, páginas, logs ou mensagens.

### 7.2 Estudante

- **Create:** cadastra matrícula, CPF, MC e ano de ingresso.
- **Read:** lista estudantes e exibe ficha com usuário e vínculos relacionados.
- **Update:** permite alterar CPF referenciado, MC e ano; matrícula é imutável.
- **Delete:** exclui somente quando não existem vínculos.
- Matrícula é única e cada CPF pode ter somente um estudante.
- O CPF informado precisa existir em `usuario`.

### 7.3 Vinculo

- **Create:** cria um vínculo individual com ID interno, estudante, curso,
  datas e status.
- **Read:** lista os vínculos e apresenta ficha individual.
- **Update:** altera estudante, curso, datas e status, preservando o ID.
- **Delete:** remove somente o vínculo selecionado, sem excluir estudante ou
  curso.
- Estudante e curso precisam existir.
- A combinação estudante/curso não pode se repetir.
- Status e datas são validados; a saída não pode ser anterior à entrada.

### 7.4 Curso

- **Create:** cadastra nome, grau, turno, campus e nível; o ID é gerado
  internamente.
- **Read:** lista cursos sem destacar desnecessariamente o ID e oferece ficha
  individual.
- **Update:** altera os dados acadêmicos e mantém o ID.
- **Delete:** exclui somente quando não existem vínculos.
- A combinação nome, turno, campus e nível é verificada contra duplicidade
  quando todos esses campos estão informados.
- Grau, turno e nível respeitam os domínios definidos.

### 7.5 Admissão conjunta

A rota `/admissoes/nova` cadastra `usuario`, `estudante` e o vínculo inicial em
um único fluxo. Todos os dados são validados antes da primeira escrita. No modo
mock, o repositório mantém um snapshot das quatro coleções e restaura o estado
anterior se qualquer etapa falhar, evitando documentos parciais. A transação
real com sessão PyMongo ainda será configurada para o Atlas.

## 8. Evidências do efeito de cada método

Esta seção deve ser preenchida após a implantação autorizada no Atlas. Cada
figura deve mostrar somente os campos necessários, ocultando senha, URI,
credenciais, nomes de usuário do cluster e demais dados sensíveis.

### 8.1 Evidências — usuario

| Método | Operação | Estado antes | Estado depois | Evidência |
|---|---|---|---|---|
| Create | Cadastro de usuário | CPF/login não existentes | Documento criado em `usuario` | [INSERIR FIGURA 1 — Coleção usuario antes do cadastro]<br>[INSERIR FIGURA 2 — Documento de usuario criado no MongoDB] |
| Read | Listagem e ficha | Documento existente | Consulta retorna dados permitidos | [INSERIR FIGURA 4 — Consulta de usuario sem retornar a senha] |
| Update | Alteração de nome, contato ou login | Documento com valores anteriores | Mesmo CPF com valores atualizados | [INSERIR FIGURA 3 — Documento de usuario após atualização] |
| Delete | Exclusão sem estudante relacionado | Documento existente | Documento ausente da coleção | [INSERIR FIGURA 5 — Coleção usuario após exclusão] |

### 8.2 Evidências — estudante

| Método | Operação | Estado antes | Estado depois | Evidência |
|---|---|---|---|---|
| Create | Cadastro referenciando usuário | Usuário existe; matrícula não existe | Documento criado em `estudante` | [INSERIR FIGURA 6 — Coleção estudante antes do cadastro]<br>[INSERIR FIGURA 7 — Documento de estudante criado] |
| Read | Listagem e ficha | Documento existente | Consulta mostra estudante e CPF referenciado | [INSERIR FIGURA 8 — Consulta da ficha de estudante] |
| Update | Alteração de MC ou ano | Valores acadêmicos anteriores | Documento com novos valores | [INSERIR FIGURA 9 — Documento de estudante após atualização] |
| Delete | Exclusão sem vínculo | Documento existente | Documento ausente; usuário preservado | [INSERIR FIGURA 10 — Coleção estudante após exclusão] |

### 8.3 Evidências — vinculo

| Método | Operação | Estado antes | Estado depois | Evidência |
|---|---|---|---|---|
| Create | Vínculo entre estudante e curso | Estudante/curso existem; combinação não existe | Documento criado em `vinculo` | [INSERIR FIGURA 11 — Coleção vinculo antes do cadastro]<br>[INSERIR FIGURA 12 — Documento de vinculo criado] |
| Read | Listagem e ficha | Documento existente | Consulta mostra referências e status | [INSERIR FIGURA 13 — Consulta da ficha de vinculo] |
| Update | Alteração de status ou datas | Valores anteriores | Mesmo `idVinculo` com novos valores | [INSERIR FIGURA 14 — Documento de vinculo após atualização] |
| Delete | Exclusão individual | Vínculo selecionado existente | Somente esse vínculo ausente; estudante/curso preservados | [INSERIR FIGURA 15 — Coleção após exclusão individual do vinculo] |

### 8.4 Evidências — curso

| Método | Operação | Estado antes | Estado depois | Evidência |
|---|---|---|---|---|
| Create | Cadastro de curso | Combinação acadêmica não existente | Documento criado em `curso` | [INSERIR FIGURA 16 — Coleção curso antes do cadastro]<br>[INSERIR FIGURA 17 — Documento de curso criado] |
| Read | Listagem e ficha | Documento existente | Consulta mostra dados acadêmicos | [INSERIR FIGURA 18 — Consulta da ficha de curso] |
| Update | Alteração de nome, turno, campus ou nível | Valores anteriores | Mesmo ID com valores atualizados | [INSERIR FIGURA 19 — Documento de curso após atualização] |
| Delete | Exclusão sem vínculos | Curso existente e não referenciado | Documento ausente da coleção | [INSERIR FIGURA 20 — Coleção curso após exclusão] |

### 8.5 Evidências de restrições e fluxo conjunto

- [INSERIR FIGURA 21 — CPF ou login duplicado bloqueado]
- [INSERIR FIGURA 22 — Matrícula duplicada bloqueada]
- [INSERIR FIGURA 23 — Vínculo duplicado bloqueado]
- [INSERIR FIGURA 24 — Exclusão de curso referenciado bloqueada]
- [INSERIR FIGURA 25 — Exclusão de estudante com vínculo bloqueada]
- [INSERIR FIGURA 26 — Exclusão individual de vínculo com estudante e curso preservados]
- [INSERIR FIGURA 27 — Admissão conjunta com usuario, estudante e vínculo criados]
- [INSERIR FIGURA 28 — Falha na admissão sem documentos parciais]

Para cada evidência, recomenda-se registrar a tela da aplicação e o estado
correspondente da coleção no MongoDB, sempre sem exibir a senha.

## 9. Testes realizados

Foram executados **32 testes automatizados**, todos aprovados. Os testes
confirmaram:

- CRUD completo das quatro coleções;
- CPF, login, matrícula, curso e vínculo duplicados;
- usuário, estudante e curso inexistentes nas referências;
- bloqueio de exclusões que deixariam referências órfãs;
- exclusão individual do vínculo;
- senha removida dos retornos e do HTML;
- senha vazia preservada durante edição;
- campos opcionais;
- rollback da admissão conjunta;
- rotas Flask principais, fichas, edições e exclusões;
- páginas de erro tratadas;
- modo mock sem criação de cliente de rede;
- parser SQL, mapeamento das 16 coleções, duplicidades e referências no ETL.

Resultado confirmado da suíte local:

```text
Ran 32 tests

OK
```

Os testes foram executados com `mongomock`. Eles não substituem os testes de
integração com validators, índices, sessões e transações do MongoDB real. A
suíte deverá ser repetida em ambiente Atlas autorizado.

## 10. Como executar

### 10.1 Criar e ativar o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 10.2 Instalar dependências

```bash
python -m pip install -r requirements.txt
```

### 10.3 Executar os testes locais

```bash
python -m unittest discover -s tests -v
```

### 10.4 Executar a aplicação em modo mock

```bash
MONGODB_MODE=mock flask --app app run --debug
```

Com dados temporários de demonstração explicitamente habilitados:

```bash
MONGODB_MODE=mock DEMO_SEED=1 flask --app app run --debug
```

### 10.5 Dry-run do setup

```bash
python setup_banco.py --dry-run
```

### 10.6 Dry-run do ETL

```bash
python ETL.py --input universidade-dump-engdados.sql --dry-run
```

### 10.7 MongoDB Atlas — pendente

Os comandos abaixo são apenas o registro do procedimento futuro. Eles não foram
executados e somente devem ser usados após autorização, backup, preflight e
configuração segura das variáveis de ambiente, sem registrar valores no Git:

```bash
# PENDENTE — não executado
MONGODB_MODE=atlas python setup_banco.py --apply

# PENDENTE — não executado
MONGODB_MODE=atlas python ETL.py --input universidade-dump-engdados.sql --apply
```

A aplicação Flask ainda aceita apenas `MONGODB_MODE=mock`. Antes do CRUD real,
será necessário injetar o adapter PyMongo e configurar transações reais.

## 11. Estado atual e pendências

### Concluído localmente

- modelagem das 16 estruturas;
- validators e índices definidos no código;
- parser e ETL executados em dry-run;
- 238 registros válidos no dry-run;
- CRUD das quatro coleções canônicas;
- interface Flask responsiva;
- admissão conjunta com rollback em memória;
- 32 testes automatizados locais aprovados;
- documentação do mapeamento e da execução.

### Pendente

- preencher nomes dos integrantes;
- preencher link do repositório GitHub;
- confirmar e configurar MongoDB Atlas hospedado em AWS;
- realizar backup e preflight do banco remoto;
- executar `setup_banco.py --apply` no ambiente autorizado;
- executar `ETL.py --apply` no ambiente autorizado;
- implementar/injetar o adapter PyMongo da aplicação Flask;
- configurar transações reais da admissão conjunta;
- testar todos os CRUDs no MongoDB real;
- produzir as capturas das Figuras 1 a 28;
- preencher as evidências de antes e depois;
- comprovar o efeito de cada método durante a avaliação.

### Observações de consistência da documentação atual

Foram encontradas duas instruções incompletas ou imprecisas no `README.md`:

1. Os exemplos de comandos remotos mostram `--apply`, mas não mostram que a
   configuração atual também exige `MONGODB_MODE=atlas`. Sem essa variável, os
   comandos são recusados pela configuração segura.
2. O README afirma que `.env.example` contém “somente os nomes das variáveis”.
   O arquivo também contém valores locais não sensíveis, como
   `MONGODB_MODE=mock` e `DEMO_SEED=0`. Não há credenciais no arquivo, mas a
   frase não é literalmente correta.

Essas observações não alteram o código nem invalidam os testes locais. A
documentação de mapeamento está coerente ao marcar Atlas e transações reais como
pendências.

## 12. Conclusão

O mapeamento das 16 estruturas, o CRUD das quatro coleções obrigatórias, a
interface Flask, o ETL em dry-run e os testes locais foram concluídos. Os 32
testes automatizados foram aprovados em `mongomock`, sem conexão de rede.

A validação final ainda depende da configuração autorizada do MongoDB Atlas, da
aplicação dos schemas e dados, dos testes do CRUD no banco real e da inclusão das
evidências visuais do efeito de cada método. Portanto, este relatório registra
uma implementação local validada, mas não declara a Parte 2 integralmente
concluída.
