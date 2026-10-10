from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from os import environ
from time import monotonic, sleep
from uuid import uuid4

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from tests.utils import ObjectGenerator, RequestGenerator


def assert_isolated_database(connection):
    identity = connection.execute(
        text("SELECT current_database() AS name, inet_server_port() AS port")
    ).mappings().one()
    assert identity["name"] == "bootcamp_credit_fix", "Banco de regressao incorreto"
    assert identity["port"] == 55440, "Porta do banco de regressao incorreta"


@pytest.fixture(scope="module")
def credit_database():
    database_url = environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL do banco isolado nao configurada")
    url = make_url(database_url)
    if (
        url.get_backend_name() != "postgresql"
        or url.database != "bootcamp_credit_fix"
        or url.port != 55440
        or url.host not in ("127.0.0.1", "localhost")
    ):
        pytest.skip("DATABASE_URL nao aponta para o PostgreSQL isolado bootcamp_credit_fix:55440")
    assert environ.get("API_PORT") == "3309", "Porta da API de regressao incorreta"
    assert environ.get("SERVER_LOCALHOST") in ("127.0.0.1", "localhost"), "Host da API de regressao incorreto"
    engine = create_engine(database_url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            assert_isolated_database(connection)
        response = requests.get(
            f"http://{environ['SERVER_LOCALHOST']}:3309/health_check", timeout=3
        )
        assert response.status_code == 204, f"API de regressao devolveu {response.status_code} na verificacao de saude"
        yield engine
    finally:
        engine.dispose()


def persisted_state(engine, client):
    queries = {
        "accounts": """
            SELECT id, account_key, balance, status_id
            FROM public.account WHERE client_id = :client_id ORDER BY id
        """,
        "lines": """
            SELECT id, credit_line_key, approved_limit, available_limit, interest_rate, status
            FROM public.credit_line WHERE client_id = :client_id ORDER BY id
        """,
        "invoices": """
            SELECT i.id, i.invoice_key, i.credit_line_id, s.enumerator AS status,
                   i.billing_cycle, i.amount_due, i.due_date
            FROM public.credit_invoice i
            JOIN public.credit_line l ON l.id = i.credit_line_id
            JOIN public.invoice_status s ON s.id = i.status_id
            WHERE l.client_id = :client_id ORDER BY i.id
        """,
        "events": """
            SELECT e.id, e.invoice_id, e.status_id, e.event_datetime
            FROM public.invoice_status_event e
            JOIN public.credit_invoice i ON i.id = e.invoice_id
            JOIN public.credit_line l ON l.id = i.credit_line_id
            WHERE l.client_id = :client_id ORDER BY e.id
        """,
        "operations": """
            SELECT o.id, o.operation_key, k.enumerator AS kind, o.amount, o.fee,
                   o.idempotency_key, o.request_hash, o.origin_account_id, o.target_account_id
            FROM public.account_operation o
            JOIN public.operation_kind k ON k.id = o.kind_id
            WHERE o.actor_client_id = :client_id ORDER BY o.id
        """,
        "entries": """
            SELECT t.id, t.operation_id, t.account_id, y.enumerator AS type, t.amount
            FROM public.account_transaction t
            JOIN public.account a ON a.id = t.account_id
            JOIN public.transaction_type y ON y.id = t.type_id
            WHERE a.client_id = :client_id ORDER BY t.id
        """,
    }
    with engine.connect() as connection:
        assert_isolated_database(connection)
        client_id = connection.execute(
            text("SELECT id FROM public.client WHERE client_key = :client_key"),
            {"client_key": client["client_key"]},
        ).scalar_one()
        return {
            name: [dict(row) for row in connection.execute(text(query), {"client_id": client_id}).mappings()]
            for name, query in queries.items()
        }


def client_for_endpoint(endpoint):
    client = ObjectGenerator.create_active_client()
    if endpoint != "request":
        assert ObjectGenerator.open_credit_line(client)["limit_cents"] == 100000
        status, response = RequestGenerator.POST_credit_withdraw(
            client["client_key"], client["token"], str(uuid4()), 10000
        )
        assert status == 201, response
    return client


def call_credit_endpoint(endpoint, client, token):
    if endpoint == "request":
        return RequestGenerator.POST_credit(client["client_key"], token)
    if endpoint == "withdraw":
        return RequestGenerator.POST_credit_withdraw(client["client_key"], token, str(uuid4()), 1000)
    return RequestGenerator.POST_invoice_pay(client["client_key"], token, str(uuid4()), {"amount": 1000})


@pytest.mark.parametrize("endpoint", ["request", "withdraw", "pay"])
def test_credit_routes_refuse_another_client_without_side_effects(credit_database, endpoint):
    owner = client_for_endpoint(endpoint)
    intruder = ObjectGenerator.create_active_client()
    owner_before = persisted_state(credit_database, owner)
    intruder_before = persisted_state(credit_database, intruder)

    status, response = call_credit_endpoint(endpoint, owner, intruder["token"])

    assert persisted_state(credit_database, owner) == owner_before
    assert persisted_state(credit_database, intruder) == intruder_before
    assert status == 401, response
    assert response["code"] == "QIT003005"


@pytest.mark.parametrize("endpoint", ["request", "withdraw", "pay"])
def test_credit_routes_refuse_operator_token_without_side_effects(credit_database, operator_token, endpoint):
    owner = client_for_endpoint(endpoint)
    before = persisted_state(credit_database, owner)

    status, response = call_credit_endpoint(endpoint, owner, operator_token)

    assert persisted_state(credit_database, owner) == before
    assert status == 401, response
    assert response["code"] == "QIT003005"


def wait_for_blocked_requests(engine, holder_pid, expected, futures):
    deadline = monotonic() + 10
    while monotonic() < deadline:
        with engine.connect() as connection:
            assert_isolated_database(connection)
            blocked = connection.execute(
                text("""
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database() AND pid <> :holder_pid
                      AND wait_event_type = 'Lock' AND query ILIKE '%FOR UPDATE%'
                """),
                {"holder_pid": holder_pid},
            ).scalar_one()
        if blocked >= expected:
            return
        for future in futures:
            if future.done():
                pytest.fail(f"Requisicao terminou antes da sobreposicao: {future.result()}")
        sleep(0.02)
    pytest.fail(f"Nao houve {expected} requisicoes HTTP concorrentes bloqueadas no banco")


def overlapping_requests(engine, client, first_call, second_call):
    executor = ThreadPoolExecutor(max_workers=2)
    futures = []
    try:
        with engine.connect() as connection:
            assert_isolated_database(connection)
            holder_pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
            connection.execute(
                text("SELECT id FROM public.account WHERE account_key = :account_key FOR UPDATE"),
                {"account_key": client["account_key"]},
            ).scalar_one()
            futures.append(executor.submit(first_call))
            wait_for_blocked_requests(engine, holder_pid, 1, futures)
            futures.append(executor.submit(second_call))
            wait_for_blocked_requests(engine, holder_pid, 2, futures)
            connection.commit()
        return [future.result(timeout=15) for future in futures]
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def test_concurrent_withdrawals_approve_only_one_and_keep_money_consistent(credit_database):
    client = ObjectGenerator.create_active_client()
    assert ObjectGenerator.open_credit_line(client)["limit_cents"] == 100000
    keys = [str(uuid4()), str(uuid4())]

    responses = overlapping_requests(
        credit_database,
        client,
        lambda: RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], keys[0], 60000),
        lambda: RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], keys[1], 60000),
    )

    assert sorted(status for status, _ in responses) == [201, 422], responses
    approved = next(body for status, body in responses if status == 201)
    rejected = next(body for status, body in responses if status == 422)
    assert approved["fee_charged"] == 1200
    assert approved["total_cost"] == 61200
    assert rejected["status"] == "REJECTED"
    state = persisted_state(credit_database, client)
    assert len(state["accounts"]) == len(state["lines"]) == len(state["invoices"]) == 1
    assert state["accounts"][0]["balance"] == 60000
    assert state["invoices"][0]["amount_due"] == 61200
    assert state["lines"][0]["available_limit"] == 38800
    assert state["lines"][0]["approved_limit"] == 100000
    assert len(state["operations"]) == len(state["entries"]) == 1
    operation = state["operations"][0]
    entry = state["entries"][0]
    assert (operation["kind"], operation["amount"], operation["fee"]) == ("deposit", 60000, 1200)
    assert operation["idempotency_key"] in keys
    assert (entry["operation_id"], entry["type"], entry["amount"]) == (operation["id"], "deposit", 60000)
    assert ObjectGenerator.get_balance(client) == 60000


def test_concurrent_payment_and_withdrawal_finish_with_consistent_debt_and_limit(credit_database):
    client = client_for_endpoint("pay")
    pay_key, withdraw_key = str(uuid4()), str(uuid4())

    responses = overlapping_requests(
        credit_database,
        client,
        lambda: RequestGenerator.POST_invoice_pay(client["client_key"], client["token"], pay_key, {"amount": 3000}),
        lambda: RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], withdraw_key, 5000),
    )

    assert [status for status, _ in responses] == [200, 201], responses
    state = persisted_state(credit_database, client)
    assert len(state["accounts"]) == len(state["lines"]) == len(state["invoices"]) == 1
    assert state["accounts"][0]["balance"] == 12000
    assert state["invoices"][0]["amount_due"] == 12300
    assert state["lines"][0]["available_limit"] == 87700
    assert state["invoices"][0]["amount_due"] + state["lines"][0]["available_limit"] == 100000
    assert responses[0][1]["paid_amount"] == 3000
    assert responses[1][1]["total_cost"] == 5100
    assert len(state["operations"]) == len(state["entries"]) == 3
    assert sorted((o["kind"], o["amount"], o["fee"]) for o in state["operations"]) == [
        ("deposit", 5000, 100), ("deposit", 10000, 200), ("withdraw", 3000, 0)
    ]
    assert sorted((e["type"], e["amount"]) for e in state["entries"]) == [
        ("deposit", 5000), ("deposit", 10000), ("withdraw", 3000)
    ]
    assert ObjectGenerator.get_balance(client) == 12000


def test_invoice_insert_failure_rolls_back_the_credit_line_and_retry_is_coherent(credit_database):
    client = ObjectGenerator.create_active_client()
    before = persisted_state(credit_database, client)
    suffix = uuid4().hex
    trigger_name = f"test_credit_invoice_failure_{suffix}"
    function_name = f"test_credit_invoice_failure_fn_{suffix}"
    try:
        with credit_database.begin() as connection:
            assert_isolated_database(connection)
            client_id = connection.execute(
                text("SELECT id FROM public.client WHERE client_key = :client_key"),
                {"client_key": client["client_key"]},
            ).scalar_one()
            connection.execute(text(f"""
                CREATE FUNCTION public.{function_name}() RETURNS trigger AS $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM public.credit_line
                               WHERE id = NEW.credit_line_id AND client_id = {int(client_id)}) THEN
                        RAISE EXCEPTION 'controlled invoice insert failure';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """))
            connection.execute(text(f"""
                CREATE TRIGGER {trigger_name} BEFORE INSERT ON public.credit_invoice
                FOR EACH ROW EXECUTE FUNCTION public.{function_name}()
            """))
        status, response = RequestGenerator.POST_credit(client["client_key"], client["token"])
    finally:
        with credit_database.begin() as connection:
            assert_isolated_database(connection)
            connection.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name} ON public.credit_invoice"))
            connection.execute(text(f"DROP FUNCTION IF EXISTS public.{function_name}()"))

    assert status == 500, response
    failed = persisted_state(credit_database, client)
    assert failed["lines"] == failed["invoices"] == failed["events"] == []
    assert failed == before
    status, response = RequestGenerator.POST_credit(client["client_key"], client["token"])
    assert status == 201, response
    state = persisted_state(credit_database, client)
    assert len(state["lines"]) == len(state["invoices"]) == len(state["events"]) == 1
    line, invoice, event = state["lines"][0], state["invoices"][0], state["events"][0]
    assert line["credit_line_key"] == response["credit_line_key"]
    assert line["approved_limit"] == line["available_limit"] == response["limit_cents"] == 100000
    assert line["interest_rate"] == Decimal("0.0200")
    assert line["status"] == "ACTIVE"
    assert invoice["credit_line_id"] == line["id"]
    assert invoice["status"] == "open"
    assert invoice["amount_due"] == 0
    assert event["invoice_id"] == invoice["id"]
    assert state["accounts"] == before["accounts"]
    assert state["operations"] == state["entries"] == []
