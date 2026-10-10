# Bootcamp QI Tech — projeto base da API

Projeto base do Bootcamp: uma API REST em **Python + FastAPI**, com banco
**PostgreSQL**, rodando em **Docker**.

Você não precisa saber programar para começar. A API e o banco sobem
no **Docker**, então você não instala nem um nem outro na sua máquina.
Os **testes** rodam no seu Python — são dois comandos, e a seção 2
mostra os dois.

---

## 0. O que você precisa ter instalado

São três coisas.

| O quê | Para quê | Como conferir |
|---|---|---|
| **Docker** (com o Docker Desktop no Mac/Windows) | roda a API e o banco | `docker compose version` |
| **Git** | trazer o projeto para o seu computador | `git --version` |
| **Python 3.11** | rodar os testes (seção 2) | `python3 --version` |

Abra o terminal e rode os três comandos da coluna da direita. Se todos
responderem um número de versão, você está pronto.

> **Por que o Python, se tudo roda no Docker?** Porque os testes rodam
> FORA dele, na sua máquina, contra a API que está de pé no container.
> O ganho é o ciclo: você salva um teste e roda na hora, sem esperar
> imagem nenhuma ser montada. O preço está explicado na seção 2.

> **`docker compose version` deu erro?** Sua instalação do Docker é
> antiga demais (ou o Docker não está ligado). No Mac e no Windows,
> abra o **Docker Desktop** e espere a baleia parar de se mexer. Se o
> comando continuar falhando, reinstale pelo site oficial —
> o `docker compose` (com **espaço**) vem junto desde 2022.

Nada além destes três. Se em algum momento este projeto pedir que você
instale outro PROGRAMA, é um bug do projeto — avise a gente. (As
bibliotecas Python que os testes usam são outra conversa: elas entram
com um `pip install` na seção 2, dentro de uma pasta do próprio
projeto, e somem quando você apaga essa pasta.)

---

## 1. Rodando pela primeira vez

Copie a configuração de desenvolvimento antes de iniciar:

```bash
cp .env.example .env
docker compose up
```

No PowerShell, use `Copy-Item .env.example .env` para fazer a cópia.
O arquivo inclui valores sintéticos para o operador, a conta de receita,
o JWT e o banco. Essas credenciais servem apenas para desenvolvimento.

O Docker baixa o Python, sobe o banco e o mock server, cria as tabelas,
prepara o operador e a conta de receita e liga a API. Na
primeira vez demora alguns minutos; depois é quase instantâneo.

São três serviços de pé:

| Serviço | O que é |
|---|---|
| `api` | a API que responde às suas requisições |
| `db` | o banco de dados (PostgreSQL) |
| `mock-server` | simula as respostas de KYC, antifraude e risco de crédito |

Quando aparecer `Application startup complete`, a API está no ar. Abra
no navegador:

### 👉 http://localhost:3000

Você vai ver isto:

```json
{"service":"bootcamp-api","id":"8"}
```

Pouca coisa, e de propósito: essa rota só diz "estou viva, e eu sou este
serviço". Mas você acabou de fazer uma **requisição HTTP** — a mesma
coisa que o navegador faz ao abrir qualquer site.

### Cadastro, login e consulta

As rotas de negócio exigem `INTERNAL-TOKEN`. O cadastro e os logins são
abertos para quem ainda não tem JWT; as consultas e operações protegidas
exigem também `Authorization: Bearer <token>`.

Os comandos abaixo usam Bash. No Windows, você pode executá-los no Git Bash.
Use os valores de token, porta e senhas do seu `.env` se tiver alterado os padrões.

#### 1. Criar um cliente

```bash
curl -X POST http://localhost:3000/client \
  -H "INTERNAL-TOKEN: default_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Maria da Silva",
    "email": "maria.silva@exemplo.com.br",
    "document_number": "529.982.247-25",
    "password": "maria123",
    "birthdate": "1990-05-17"
  }'
```

A resposta é `201` com `client_key`. Copie a chave recebida. O mock de
KYC e o de antifraude decidem se o cadastro fica `approved` ou `rejected`.
Quando aprovado, o cliente recebe uma conta com saldo zero.

#### 2. Fazer login como cliente

```bash
curl -X POST http://localhost:3000/auth/login \
  -H "INTERNAL-TOKEN: default_token" \
  -H "Content-Type: application/json" \
  -d '{"document_number":"529.982.247-25","password":"maria123"}'
```

A resposta é `200` com `token`. Guarde o JWT e a chave do cadastro:

```bash
CLIENT_TOKEN='cole_o_token_recebido'
CLIENT_KEY='cole_a_client_key_recebida'
```

#### 3. Consultar o próprio cadastro

```bash
curl "http://localhost:3000/client/$CLIENT_KEY" \
  -H "INTERNAL-TOKEN: default_token" \
  -H "Authorization: Bearer $CLIENT_TOKEN"
```

A resposta `200` contém `client_key`, `name`, `email`, `document_number`,
`birthdate`, `status` e `accounts`. Cada conta informa `account_key`,
`balance` e `status`. O saldo é uma string em reais, como `"0.00"`.
O histórico não vem nessa resposta; há rotas próprias para ele.

#### 4. Fazer login como operador

```bash
curl -X POST http://localhost:3000/auth/operator/login \
  -H "INTERNAL-TOKEN: default_token" \
  -H "Content-Type: application/json" \
  -d '{"document_number":"529.982.247-25","password":"admin123"}'
```

Use `ADMIN_DOCUMENT_NUMBER` e `ADMIN_INITIAL_PASSWORD` do `.env`.
O operador é criado quando o serviço inicia. Copie o token retornado:

```bash
OPERATOR_TOKEN='cole_o_token_do_operador'
```

#### 5. Consultar o histórico de status

```bash
curl "http://localhost:3000/client/$CLIENT_KEY/status-events" \
  -H "INTERNAL-TOKEN: default_token" \
  -H "Authorization: Bearer $OPERATOR_TOKEN"
```

Essa rota exige JWT de **operador**, inclusive quando quem consulta é o
próprio titular. A resposta `200` tem `status_events`: cada item contém
`status`, `event_datetime` e `operator_key`. Eventos automáticos têm
`operator_key: null`; mudanças manuais registram a chave do operador.

O histórico da conta segue o mesmo formato e a mesma autorização:
`GET /account/{account_key}/status-events`.

### Rotas disponíveis

| Método e rota | O que faz | Autenticação |
|---|---|---|
| `GET /` | identifica o serviço | aberta |
| `GET /health_check` | confirma que a API responde; retorna 204 | aberta |
| `POST /client` | cadastra o cliente | token interno |
| `POST /auth/login` | autentica o cliente | token interno |
| `POST /auth/operator/login` | autentica o operador | token interno |
| `POST /auth/logout` | revoga o JWT | token interno + JWT |
| `GET /client/{client_key}` | consulta cadastro e contas | token interno + JWT autorizado |
| `GET /clients` | lista clientes com filtros e paginação | token interno + JWT de operador |
| `PUT /client/{client_key}` | altera o status do cadastro | token interno + JWT de operador |
| `GET /client/{client_key}/status-events` | histórico do cadastro | token interno + JWT de operador |
| `PATCH /account/{account_key}` | altera o status da conta | token interno + JWT de operador |
| `GET /account/{account_key}/status-events` | histórico da conta | token interno + JWT de operador |
| `POST /account/{account_key}/deposit` | deposita na conta | token interno + JWT do titular |
| `POST /account/{account_key}/withdraw` | retira da conta | token interno + JWT do titular |
| `POST /account/{account_key}/transfer` | transfere entre contas | token interno + JWT do titular da origem |
| `GET /account/{account_key}/extract` | extrato paginado | token interno + JWT do titular |
| `POST /client/{client_key}/credit` | solicita crédito ao bureau de risco | token interno + JWT do titular |
| `POST /client/{client_key}/credit/withdraw` | resgata crédito | token interno + JWT do titular |
| `POST /client/{client_key}/invoice/pay` | paga a fatura | token interno + JWT do titular |

Depósito, retirada, transferência, resgate de crédito e pagamento de fatura
recebem também `Idempotency-Key`. Os valores dessas operações são inteiros
em **centavos**, por exemplo `{"amount":1000}` para R$ 10,00.
A transferência usa também `account_to_key` para indicar o destino.

As listagens usam `limit` e `page`, com página inicial zero. O extrato
aceita `start_date` e `end_date` no formato `YYYY-MM-DD`. Consulte os
arquivos de `src/schemas/` e os testes de integração para cada contrato.

Para desligar tudo: `Ctrl+C` no terminal da API e depois

```bash
docker compose down
```

---

## 2. Rodando os testes

Os testes rodam **na sua máquina**, contra a API que está de pé no
Docker. Use um banco exclusivo para testes: alguns casos apagam e
recriam todas as tabelas de `public`. Não execute a suíte em um banco
com dados que deseja manter.

Crie `.env` com a seção 1. O arquivo deve apontar para a mesma API e o
mesmo banco usados pelo Docker. `TEST_ALLOW_DATABASE_MUTATION=1` permite
explicitamente a limpeza e os testes de integridade; `APP_ENV` deve ser
`local` ou `test`. Sem essa configuração, os testes falham antes de
alterar o banco. Os testes de crédito aceitam o nome e as portas definidos
no ambiente, inclusive portas publicadas diferentes das internas do Docker.

**Uma vez só — instalar as dependências de teste:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

#criar uma venv com python 3.11

O `.venv` é uma pasta com um Python só deste projeto. Ele existe pra que
instalar algo aqui não mexa no Python da sua máquina — e pra que apagar a
pasta desfaça tudo. No Windows, a segunda linha é
`.venv\Scripts\activate`.

**Toda vez — com a API de pé, em outro terminal:**

```bash
pytest -ra
```

A API precisa estar respondendo antes. Se você acabou de dar
`docker compose up`, espere o `(healthy)` aparecer — é o healthcheck do
`docker-compose.yml` dizendo que a porta já atende. Sem isso, o primeiro
teste bate numa porta que ainda não responde.

O resultado sai assim:

```
tests/integration/test_healthcheck.py::TestHealthCheck::test_home PASSED
...
```

Para rodar só um arquivo (ou só um teste), acrescente o caminho:

```bash
pytest -v tests/integration/test_healthcheck.py
```

Os testes leem o seu `.env` sozinhos (é o `tests/conftest.py` que faz
isso). `SERVER_LOCALHOST` e `API_PORT` indicam a API; `DATABASE_URL`
indica o banco acessível pela máquina que roda o pytest. O timeout HTTP
padrão é de 30 segundos e pode ser ajustado com `TEST_HTTP_TIMEOUT`.

Para salvar o resultado completo no PowerShell:

```powershell
pytest -ra --tb=short 2>&1 | Tee-Object pytest-resultados.txt
```

`passed` indica testes aprovados. `failed` indica uma asserção que não
foi atendida. `error` indica falha de preparação, como login do operador
ou conexão com o banco. `xfail` indica defeitos conhecidos ainda marcados
na suíte. Para executá-los como falhas normais, use `pytest --runxfail -ra`.

Os testes de integração conversam com a API **por HTTP**, como um cliente.
Os testes unitários em `tests/test_database_configuration.py` conferem as
guardas de configuração e o seed com acesso ao banco e HTTP simulados.

> Os cenários nascem pela API. `tests/utils/db_utils.py` acessa o banco
> para limpar os dados e repor o operador e a conta de receita. Os testes
> de integridade de crédito também usam SQL para conferir valores gravados,
> controlar concorrência e simular falha na criação da fatura. As guardas
> exigem permissão explícita e confirmam o banco configurado antes dessas
> alterações. Execute a suíte sequencialmente, sem `pytest-xdist`.

Isso tem uma consequência bonita: **este projeto inteiro já foi reescrito
de um framework para outro, e nenhum teste precisou mudar.** Quando o
teste descreve o combinado em vez de descrever o código, ele sobrevive à
reforma.

## 3. Quando dá errado

Os tropeços mais comuns, com a mensagem que você vai ver:

### `port is already allocated`

```
Bind for 0.0.0.0:5432 failed: port is already allocated
```

Outro programa da sua máquina já usa aquela porta (é comum ter um
Postgres instalado ocupando a 5432). Não precisa descobrir qual: escolha
outras portas livres. É pra isto que serve o `.env` —

```bash
cp .env.example .env
```

— e, dentro dele, troque os números destas duas linhas:

```
API_PORT=3001
DB_PORT=5433
```

Mexeu no `DB_PORT`? Então mude **também** a porta da `DATABASE_URL`, no
mesmo arquivo:

```
DATABASE_URL=postgresql+psycopg2://bootcamp:bootcamp@localhost:5433/bootcamp
```

São dois lugares porque são dois pontos de vista. O `DB_PORT` diz em
que porta **da sua máquina** o banco aparece; a `DATABASE_URL` é o
endereço que os testes usam para chegar nele de fora do Docker. A API
lá dentro não usa nenhuma das duas — para ela o banco é `db:5432`, e
por isso essa linha está fixa no `docker-compose.yml`.

Suba de novo. Agora a API atende em http://localhost:3001 — e nos
comandos `curl` da seção 1 você troca `3000` por `3001`.

### `failed to connect to the docker API`

```
failed to connect to the docker API at unix:///var/run/docker.sock;
check if the path is correct and if the daemon is running
```

O Docker não está ligado. Abra o **Docker Desktop** (Mac/Windows) e
espere ficar verde. No Linux: `sudo systemctl start docker`.

### `Não consegui falar com a API` / `Não consegui falar com o banco`

Só aparece no atalho local (fora do Docker). Quer dizer que a API ou o
banco não estão de pé, ou que a porta no seu `.env` não é a que eles
estão usando. Suba com `docker compose up` e confira as portas.

### `relation "..." does not exist`

```
psycopg2.errors.UndefinedTable: relation "minha_tabela" does not exist
```

Você mexeu no `database/database.sql`, e o banco não ficou sabendo.
Aquele arquivo roda **uma vez só: quando o banco nasce.** Depois disso o
Postgres nunca mais olha para ele — subir de novo com `docker compose
up` não adianta, e `docker compose restart db` também não.

Repare no que a mensagem faz com você: ela não diz "seu SQL não rodou",
diz que a tabela não existe. Você vai reler o seu SQL procurando um erro
de digitação que não está lá.

Para o banco nascer de novo, já com o schema novo:

```bash
docker compose down -v
docker compose up
```

O `-v` é o que apaga o volume — o disco do banco. **Ele leva junto tudo
que você tinha criado na mão**, as entidades dos `curl` da seção 1. Não
tem meio-termo: ou o banco nasce de novo com o schema novo, ou continua
com o antigo. (Em sistema de verdade é outra história — lá ninguém apaga
o banco, e a mudança de schema entra por um comando aplicado no deploy.)

### Nada disso resolveu?

Este comando desliga e limpa **este** projeto (containers, rede e o
banco com tudo dentro) para você recomeçar do zero:

```bash
docker compose down -v
docker compose up
```

Para ver o que a API está dizendo enquanto roda: `docker compose logs -f api`.

---

## 4. As pastas

```
src/
  app.py           ← liga tudo: rotas, middlewares e tratamento de erro
  database.py      ← onde a sessão de banco mora (quem cuida do ciclo
                     dela é middlewares/session_manager.py)
  constants.py     ← as configurações, lidas do ambiente

  resources/       ← recebe a requisição HTTP e devolve a resposta
                     (quem liga cada endereço a um resource é o app.py)
  schemas/         ← o formato do que entra: o JSON do corpo e os
                     parâmetros do endereço
  controllers/     ← as regras de negócio: o que pode e o que não pode
  repositories/    ← as conversas com o banco
  models/          ← as tabelas, descritas em Python
  dtos/            ← traduz o objeto do banco no JSON que sai
  errors/          ← os erros da API, cada um com seu código
  middlewares/     ← o que acontece com TODA requisição
  connectors/      ← as conversas com outros serviços
  utils/           ← as ferramentas que não são de nenhuma camada

database/
  database.sql     ← as tabelas, em SQL puro

tests/             ← os testes
```

### Por que tanta pasta?

Porque cada uma tem **um trabalho só**, e só conversa com a vizinha:

```
requisição → resource → controller → repository → banco
                 ↑           ↑
             valida o     decide o
              formato     que pode
```

O resource não sabe SQL. O repository não sabe o que é uma regra de
negócio. Um teste rápido para saber se uma linha está na pasta certa:
**nenhum `raise` mora em `resources/`** — quem recusa é o schema, antes,
ou o controller, depois. Confira você mesmo:

```bash
grep -rn "raise" src/resources/
```

Não volta nada, e isso é de propósito. Quando você precisa trocar o banco, mexe numa pasta. Quando a
regra muda, mexe na outra. É isso que permite um time inteiro trabalhar
no mesmo projeto sem pisar no pé um do outro.

---

## 5. Configuração e senhas

Toda configuração entra por **variável de ambiente** — nunca escrita no
meio do código.

- **valor padrão** → escrito no `docker-compose.yml`, na forma
  `${VARIAVEL:-padrao}` para as opções que têm um padrão de desenvolvimento.
- `.env` → **obrigatório** nesta configuração, fica só na sua máquina e
  **nunca** vai para o Git. Define JWT, operador, receita, banco e portas.
- `.env.example` → vai para o Git, e é a cópia de onde você parte. Só
  tem valor de mentirinha.

Essa separação não é frescura. Senha commitada em repositório é uma das
formas mais comuns de vazamento de dados no mundo real, e não tem
desfazer: uma vez no histórico, está lá para sempre.

Uma ressalva honesta: valor padrão de senha em arquivo versionado só
vale porque aqui é um projeto de estudo, sem dado de ninguém. Em
sistema de verdade, segredo não tem padrão — ele falta, e a aplicação
se recusa a subir sem ele.

## 6. Autenticação

As rotas de negócio pedem o token interno:

```
INTERNAL-TOKEN: default_token
```

Sem ele, a API responde **403**. `default_token` é o valor padrão; para
trocar, ponha `INTERNAL_TOKEN=outra_coisa` no seu `.env`.

A raiz e `/health_check` não exigem esse token. Cadastro e logins exigem
apenas o token interno. As demais rotas exigem também o JWT no cabeçalho
`Authorization: Bearer <token>`, com o perfil e a titularidade adequados.

---

## 7. Os códigos de erro

Todo erro da API responde no mesmo formato, com um código próprio:

```json
{
  "title": "Bad Request",
  "description": "'hello' is a required property",
  "translation": "Payload Inválido",
  "code": "QIT000001"
}
```

| Código      | Quando acontece                                  |
|-------------|--------------------------------------------------|
| `QIT000001` | o JSON enviado está fora do formato              |
| `QIT000002` | faltou o `INTERNAL-TOKEN`, ou ele está errado    |
| `QIT000010` | os parâmetros do endereço se contradizem         |
| `QIT000404` | essa rota não existe                             |
| `QIT000405` | a rota existe, mas não aceita esse método        |
| `QIT000500` | erro inesperado (o time é avisado)               |
| `QIT001001` | a entidade procurada não existe                  |
| `QIT001002` | a entidade já está num status final              |
| `QIT001003` | o CPF tem o formato certo, mas não é um CPF      |
| `QIT001004` | já existe um cadastro com esse CPF               |
| `QIT001005` | já existe um cadastro com esse e-mail            |
| `QIT001006` | a pessoa é menor de idade                        |
| `QIT001007` | a data de nascimento não existe no calendário    |
| `QIT002001` | Não foi encontrado a conta                       |
| `QIT002002` | Essa conta não está ativa                        |
| `QIT002003` | Saldo insuficiente                               |
| `QIT002004` | O valor informado não é válido                   |

Um código estável vale mais que uma mensagem bonita: quem integra com a
API programa em cima do código, não do texto.

Os números não são sorteados. Eles vêm em duas faixas:

- **`QIT000…`** — os erros que **toda** API tem: JSON errado, sem token,
  rota inexistente. Estão em `src/errors/base_error.py` e você não
  precisa mexer neles.
- **`QIT001…`** — os erros das **regras deste projeto**. Estão em
  `src/errors/custom_errors.py`, e é aí que os seus entram: o próximo
  livre é o `QIT001008`.

Não repita um número. Se repetir, a API **não sobe** — tem uma checagem
no start (`error_verification`, em `src/errors/base_error.py`) que
procura código repetido e derruba a aplicação de propósito. Parecer
chato agora é melhor que dois erros diferentes chegarem ao cliente com o
mesmo código.

---

## 8. A licença

Este projeto é **MIT** — pode usar, copiar, modificar e levar para o seu
portfólio, inclusive em trabalho pago. O único pedido é manter o arquivo
`LICENSE` junto quando você distribuir o código.
