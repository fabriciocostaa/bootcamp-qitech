from os import environ
from pathlib import Path
from re import fullmatch
from uuid import UUID, uuid4

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, OperationalError


RESET_QUERIES = [
    "DROP SCHEMA public CASCADE;",
    "CREATE SCHEMA public;",
    "GRANT ALL ON SCHEMA public TO CURRENT_USER;",
    "GRANT ALL ON SCHEMA public TO public;",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = PROJECT_ROOT / "database" / "database.sql"

DEFAULT_DATABASE_URL = "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"

DATABASE_OFFLINE = (
    "Não consegui falar com o banco em {host}:{port}.\n"
    "Ele precisa estar de pé pros testes rodarem. Suba com:  docker compose up\n"
    "Se ele já está de pé, confira a porta na DATABASE_URL do seu .env."
)


SEED_MISSING_VARIABLES = (
    "Faltam variáveis no ambiente para recriar o operador e a conta de receita: {names}.\n"
    "Elas já estão no seu .env (ADMIN_*, ACCOUNT_*, REVENUE_ACCOUNT_KEY)."
)


class DbUtils:
    """Apaga o banco inteiro e o recria do zero — quando alguém chama.

    Não existe limpeza automática neste projeto. O `rollback()` roda no
    teste que o chamar, na linha em que for chamado, e em mais lugar
    nenhum. Todos os testes dividem o mesmo banco, e cada um enxerga o
    que os anteriores deixaram pra trás.

    O nome engana um pouco: isto não desfaz uma transação. Ele derruba
    o schema `public` com tudo que estiver dentro e roda o
    `database/database.sql` de novo — tabelas vazias e os status do
    INSERT de volta.

    Depois de recriar, ele REPÕE o que a API assume que já existe: o
    operador (sem ele nenhuma rota de operador funciona) e a conta de
    receita do banco (sem ela toda transferência quebra, porque a taxa
    precisa de um destino). Esses dois nascem de um seed, não do SQL; se
    o rollback não os devolvesse, o primeiro teste de operador depois de
    uma limpeza falharia por um motivo que nada tem a ver com ele.

    Quando o seu teste precisa chamar: sempre que alguma asserção
    depender de QUANTAS linhas existem no banco — contar, listar,
    paginar, filtrar. Nesses casos `DbUtils.rollback()` é a primeira
    linha do teste, antes de criar qualquer coisa (o exemplo está em
    `tests/integration/test_sample_entities.py`). Um teste que só olha
    as entidades que ele mesmo criou, pela chave que recebeu de volta,
    não precisa de limpeza nenhuma — e fica mais rápido sem ela.

    A limpeza acontece pela mesma conexão que a aplicação usa (a
    DATABASE_URL), e não por um programa externo: quem tem Docker
    rodando já tem tudo que precisa.
    """

    @staticmethod
    def database_url() -> str:
        return environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    @staticmethod
    def check_test_database():
        if environ.get("TEST_ALLOW_DATABASE_MUTATION") != "1":
            raise RuntimeError("Defina TEST_ALLOW_DATABASE_MUTATION=1 apenas para um banco exclusivo de testes.")
        if environ.get("APP_ENV", "local") not in ("local", "test"):
            raise RuntimeError("Alteracoes de teste no banco exigem APP_ENV local ou test.")
        database_url = environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL do banco de testes nao configurada.")
        try:
            url = make_url(database_url)
        except (ArgumentError, ValueError):
            raise RuntimeError("DATABASE_URL do banco de testes invalida.") from None
        if (
            url.get_backend_name() != "postgresql"
            or url.host not in ("127.0.0.1", "localhost", "::1", "db")
            or not url.database
            or any(name in url.query for name in ("host", "hostaddr", "service"))
        ):
            raise RuntimeError("DATABASE_URL deve apontar para um PostgreSQL local exclusivo de testes.")
        return url

    @staticmethod
    def assert_test_database(connection):
        expected = DbUtils.check_test_database().database
        actual = connection.execute(text("SELECT current_database()")).scalar_one()
        if actual != expected:
            raise RuntimeError(f"Banco conectado incorreto: esperado {expected}, recebido {actual}.")

    @staticmethod
    def _check_seed_variables():
        names = ["ADMIN_DOCUMENT_NUMBER", "ADMIN_INITIAL_PASSWORD", "ACCOUNT_DOCUMENT_NUMBER",
                 "ACCOUNT_PASSWORD", "REVENUE_ACCOUNT_KEY"]
        missing = [name for name in names if not environ.get(name)]
        if missing:
            raise RuntimeError(SEED_MISSING_VARIABLES.format(names=", ".join(missing)))
        invalid = [
            name for name in ("ADMIN_DOCUMENT_NUMBER", "ACCOUNT_DOCUMENT_NUMBER")
            if not fullmatch(r"[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}", environ[name])
        ]
        revenue_key = environ["REVENUE_ACCOUNT_KEY"]
        try:
            valid_key = len(revenue_key) == 36 and str(UUID(revenue_key)) == revenue_key.lower()
        except ValueError:
            valid_key = False
        if not valid_key:
            invalid.append("REVENUE_ACCOUNT_KEY")
        for name in ("ADMIN_INITIAL_PASSWORD", "ACCOUNT_PASSWORD"):
            try:
                valid_password = 1 <= len(environ[name].encode("utf-8")) <= 72
            except UnicodeEncodeError:
                valid_password = False
            if not valid_password:
                invalid.append(name)
        if invalid:
            raise RuntimeError(f"Variaveis invalidas para recriar o banco de testes: {', '.join(invalid)}.")

    @staticmethod
    def rollback() -> None:
        DbUtils.check_test_database()
        DbUtils._check_seed_variables()
        engine = create_engine(DbUtils.database_url(), isolation_level="AUTOCOMMIT")

        try:
            with engine.connect() as connection:
                DbUtils.assert_test_database(connection)
                for query in RESET_QUERIES:
                    connection.exec_driver_sql(query)

                connection.exec_driver_sql(SCHEMA_FILE.read_text())

            DbUtils._seed(engine)
        except OperationalError:
            message = DATABASE_OFFLINE.format(host=engine.url.host, port=engine.url.port)
            raise RuntimeError(message) from None
        finally:
            engine.dispose()


    @staticmethod
    def _seed(engine) -> None:
        DbUtils._check_seed_variables()

        def hash_password(raw: str) -> str:
            return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO operator (operator_key, name, email, document_number, password_hash) "
                    "VALUES (:key, 'Admin', 'admin@example.com', :doc, :pwd)"
                ),
                {
                    "key": str(uuid4()),
                    "doc": environ["ADMIN_DOCUMENT_NUMBER"],
                    "pwd": hash_password(environ["ADMIN_INITIAL_PASSWORD"]),
                },
            )

            client_id = connection.execute(
                text(
                    "INSERT INTO client (client_key, status_id, name, email, document_number, password_hash, birthdate) "
                    "VALUES (:key, (SELECT id FROM client_status WHERE enumerator = 'approved'), "
                    "'Receita do Banco', 'receita@banco.universidade', :doc, :pwd, '2000-01-01') RETURNING id"
                ),
                {
                    "key": str(uuid4()),
                    "doc": environ["ACCOUNT_DOCUMENT_NUMBER"],
                    "pwd": hash_password(environ["ACCOUNT_PASSWORD"]),
                },
            ).scalar_one()

            connection.execute(
                text(
                    "INSERT INTO account (account_key, balance, client_id, status_id) "
                    "VALUES (:key, 0, :client_id, (SELECT id FROM account_status WHERE enumerator = 'active'))"
                ),
                {"key": environ["REVENUE_ACCOUNT_KEY"], "client_id": client_id},
            )
