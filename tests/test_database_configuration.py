import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import bcrypt
import pytest
from requests import Response
from sqlalchemy.engine import make_url

from tests.integration.credit.test_credit_integrity import assert_isolated_database
from tests.utils import db_utils, requisition
from tests.utils.db_utils import DbUtils


@pytest.fixture
def configured_database(monkeypatch):
    values = {
        "APP_ENV": "test",
        "TEST_ALLOW_DATABASE_MUTATION": "1",
        "DATABASE_URL": "postgresql+psycopg2://bootcamp:bootcamp@localhost:5433/bootcamp_test",
        "ADMIN_DOCUMENT_NUMBER": "529.982.247-25",
        "ADMIN_INITIAL_PASSWORD": "admin123",
        "ACCOUNT_DOCUMENT_NUMBER": "111.444.777-35",
        "ACCOUNT_PASSWORD": "account123",
        "REVENUE_ACCOUNT_KEY": "00000000-0000-4000-8000-000000000099",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    connection = MagicMock()
    connection.execute.return_value.scalar_one.return_value = "bootcamp_test"
    connection.execute.return_value.mappings.return_value.one.return_value = {
        "name": "bootcamp_test", "port": 5432
    }
    engine = MagicMock()
    engine.url = make_url(values["DATABASE_URL"])
    engine.connect.return_value.__enter__.return_value = connection
    factory = MagicMock(return_value=engine)
    monkeypatch.setattr(db_utils, "create_engine", factory)
    seed = MagicMock()
    monkeypatch.setattr(DbUtils, "_seed", seed)
    return factory, connection, seed


@pytest.mark.parametrize("permission", [None, "0", "false"])
def test_database_reset_requires_explicit_permission_before_connecting(configured_database, monkeypatch, permission):
    factory, connection, _ = configured_database
    if permission is None:
        monkeypatch.delenv("TEST_ALLOW_DATABASE_MUTATION")
    else:
        monkeypatch.setenv("TEST_ALLOW_DATABASE_MUTATION", permission)

    with pytest.raises(RuntimeError, match="TEST_ALLOW_DATABASE_MUTATION"):
        DbUtils.rollback()

    assert not factory.called
    assert not connection.exec_driver_sql.called


def test_database_reset_refuses_production(configured_database, monkeypatch):
    factory, connection, _ = configured_database
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="local.*test"):
        DbUtils.rollback()

    assert not factory.called
    assert not connection.exec_driver_sql.called


@pytest.mark.parametrize("name", [
    "ADMIN_DOCUMENT_NUMBER", "ADMIN_INITIAL_PASSWORD", "ACCOUNT_DOCUMENT_NUMBER",
    "ACCOUNT_PASSWORD", "REVENUE_ACCOUNT_KEY",
])
def test_database_reset_validates_seed_before_connecting(configured_database, monkeypatch, name):
    factory, connection, _ = configured_database
    monkeypatch.delenv(name)

    with pytest.raises(RuntimeError, match=name):
        DbUtils.rollback()

    assert not factory.called
    assert not connection.exec_driver_sql.called


@pytest.mark.parametrize("name, value", [
    ("ADMIN_DOCUMENT_NUMBER", "529.982.247-250"),
    ("ADMIN_DOCUMENT_NUMBER", "52998224725000"),
    ("ADMIN_DOCUMENT_NUMBER", "５２９.982.247-25"),
    ("ACCOUNT_DOCUMENT_NUMBER", "111.444.777-350"),
    ("ACCOUNT_DOCUMENT_NUMBER", "11144477735000"),
    ("ACCOUNT_DOCUMENT_NUMBER", "111.４４４.777-35"),
    ("REVENUE_ACCOUNT_KEY", "00000000-0000-4000-8000-0000000000990"),
    ("REVENUE_ACCOUNT_KEY", "x" * 36),
    ("REVENUE_ACCOUNT_KEY", "00000000000040008000000000000099"),
    ("ADMIN_INITIAL_PASSWORD", "a" * 73),
    ("ADMIN_INITIAL_PASSWORD", "é" * 37),
    ("ACCOUNT_PASSWORD", "a" * 73),
    ("ACCOUNT_PASSWORD", "😀" * 19),
])
def test_database_reset_refuses_invalid_seed_before_connecting(configured_database, monkeypatch, name, value):
    factory, connection, _ = configured_database
    monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match=name) as error:
        DbUtils.rollback()

    assert value not in str(error.value)
    assert not factory.called
    assert not connection.execute.called
    assert not connection.exec_driver_sql.called


@pytest.mark.parametrize("name, value", [
    ("ADMIN_INITIAL_PASSWORD", "a" * 72),
    ("ADMIN_INITIAL_PASSWORD", "é" * 36),
    ("ACCOUNT_PASSWORD", "b" * 72),
    ("ACCOUNT_PASSWORD", "ç" * 36),
    ("REVENUE_ACCOUNT_KEY", "A0000000-0000-4000-8000-000000000099"),
])
def test_database_reset_accepts_seed_field_boundaries(configured_database, monkeypatch, name, value):
    _, connection, seed = configured_database
    monkeypatch.setenv(name, value)

    DbUtils.rollback()

    assert connection.exec_driver_sql.call_args_list[0].args[0] == "DROP SCHEMA public CASCADE;"
    assert seed.call_count == 1


@pytest.mark.parametrize("database_url", [
    None, "sqlite:///bootcamp_test.db", "postgresql://user:pass@production.example/bootcamp",
    "postgresql://bootcamp:bootcamp@localhost:5432", "not-a-database-url",
])
def test_database_reset_refuses_an_unapproved_target(configured_database, monkeypatch, database_url):
    factory, connection, _ = configured_database
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL")
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        DbUtils.rollback()

    assert not factory.called
    assert not connection.exec_driver_sql.called


def test_database_reset_refuses_a_different_connected_database(configured_database):
    _, connection, seed = configured_database
    connection.execute.return_value.scalar_one.return_value = "production"

    with pytest.raises(RuntimeError, match="Banco"):
        DbUtils.rollback()

    assert not connection.exec_driver_sql.called
    assert not seed.called


def test_database_reset_accepts_the_configured_local_database(configured_database):
    _, connection, seed = configured_database

    DbUtils.rollback()

    assert connection.exec_driver_sql.call_args_list[0].args[0] == "DROP SCHEMA public CASCADE;"
    assert seed.call_count == 1


def test_credit_integrity_accepts_a_configured_name_and_a_docker_published_port(configured_database):
    _, connection, _ = configured_database

    assert_isolated_database(connection)


def test_test_client_uses_loopback_and_a_bounded_timeout(monkeypatch):
    monkeypatch.setenv("SERVER_LOCALHOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "3001")
    monkeypatch.delenv("TEST_HTTP_TIMEOUT", raising=False)
    response = Response()
    response.status_code = 200
    response._content = b"{}"
    send = MagicMock(return_value=response)
    monkeypatch.setattr(requisition, "request", send)

    requisition.ClientRequisition.send("GET", "/health_check")

    assert send.call_args.args[1] == "http://127.0.0.1:3001/health_check"
    assert send.call_args.kwargs["timeout"] == 30


def test_revenue_account_seed_stores_a_password_hash(configured_database, monkeypatch):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    context = SimpleNamespace(get_or_create_session=lambda: session)
    database = ModuleType("database")
    database.open_context = lambda: context
    database.clear_context = MagicMock()
    models = ModuleType("models")
    models.Client = type("Client", (), {})
    models.Account = type("Account", (), {"account_key": None})
    models.ClientStatus = SimpleNamespace(enumerator=None, APPROVED="approved")
    models.AccountStatus = SimpleNamespace(enumerator=None, ACTIVE="active")
    constants = ModuleType("constants")
    constants.REVENUE_ACCOUNT_KEY = "00000000-0000-4000-8000-000000000099"
    for name, module in (("database", database), ("models", models), ("constants", constants)):
        monkeypatch.setitem(sys.modules, name, module)
    source = Path(__file__).resolve().parents[1] / "src" / "seed_revenue_account.py"
    spec = importlib.util.spec_from_file_location("revenue_seed_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.seed_revenue_account()

    client = session.add.call_args_list[0].args[0]
    assert client.password_hash != "account123"
    assert bcrypt.checkpw(b"account123", client.password_hash.encode())
