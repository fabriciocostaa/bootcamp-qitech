import time
from os import environ
from uuid import uuid4

import jwt
import pytest

from tests.utils import ObjectGenerator, RequestGenerator


PROTECTED_ROUTES = [
    ("GET", "/client/{client_key}", None),
    ("PUT", "/client/{client_key}", {"status": "approved"}),
    ("GET", "/clients", None),
    ("POST", "/account/{account_key}/deposit", {"amount": 100}),
    ("POST", "/account/{account_key}/withdraw", {"amount": 100}),
    ("POST", "/account/{account_key}/transfer", {"account_to_key": "x", "amount": 100}),
    ("GET", "/account/{account_key}/extract", None),
    ("POST", "/auth/logout", None),
    ("POST", "/client/{client_key}/credit", None),
    ("POST", "/client/{client_key}/credit/withdraw", {"amount": 100}),
    ("POST", "/client/{client_key}/invoice/pay", {"amount": 100}),
]


def route_ids(routes):
    return [f"{method} {path}" for method, path, _body in routes]


def forge(secret: str, **overrides) -> str:
    payload = {
        "subject_key": str(uuid4()),
        "type": "client",
        "jti": str(uuid4()),
        "exp": int(time.time()) + 600,
    }
    payload.update(overrides)
    return jwt.encode(payload, secret, algorithm="HS256")


def call(method, path, body, headers_kwargs):
    path = path.format(client_key=str(uuid4()), account_key=str(uuid4()))
    return RequestGenerator._send(method, path, payload=body, **headers_kwargs)


class TestTokenValidation:
    @pytest.mark.parametrize("method,path,body", PROTECTED_ROUTES, ids=route_ids(PROTECTED_ROUTES))
    def test_every_protected_route_refuses_a_missing_token(self, method, path, body):
        status, response = call(method, path, body, {"idempotency_key": str(uuid4())})

        assert status == 401, f"{method} {path} respondeu {status} sem Authorization"
        assert response["code"] == "QIT003001"

    @pytest.mark.parametrize("method,path,body", PROTECTED_ROUTES, ids=route_ids(PROTECTED_ROUTES))
    def test_every_protected_route_refuses_a_garbage_token(self, method, path, body):
        status, response = call(method, path, body, {"jwt_token": "isto.nao.e-um-jwt", "idempotency_key": str(uuid4())})

        assert status == 401, f"{method} {path} respondeu {status} com token lixo"
        assert response["code"] == "QIT003001"

    def test_refuses_authorization_with_the_wrong_scheme(self):
        client, token = ObjectGenerator.create_authenticated_client()

        for scheme_value in [f"Basic {token}", token, "Bearer"]:
            status, response = RequestGenerator.GET_client(
                client["client_key"], authorization=scheme_value
            )
            assert status == 401, f"aceitou Authorization: {scheme_value[:20]}"
            assert response["code"] == "QIT003001"

    def test_refuses_an_empty_bearer(self):
        status, response = RequestGenerator.GET_client(str(uuid4()), authorization="Bearer ")

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_refuses_a_token_with_a_tampered_payload(self):
        client, token = ObjectGenerator.create_authenticated_client()
        header, payload, signature = token.split(".")
        flipped = "A" if payload[10] != "A" else "B"
        tampered = ".".join([header, payload[:10] + flipped + payload[11:], signature])

        status, response = RequestGenerator.GET_client(client["client_key"], tampered)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_refuses_a_token_without_signature(self):
        client, token = ObjectGenerator.create_authenticated_client()
        header, payload, _signature = token.split(".")

        status, response = RequestGenerator.GET_client(client["client_key"], f"{header}.{payload}.")

        assert status == 401
        assert response["code"] == "QIT003001"

    @pytest.mark.skipif(not environ.get("JWT_SECRET"), reason="precisa do JWT_SECRET no ambiente")
    def test_refuses_an_expired_token(self):
        client = ObjectGenerator.create_client()
        expired = forge(environ["JWT_SECRET"], subject_key=client["client_key"], exp=int(time.time()) - 10)

        status, response = RequestGenerator.GET_client(client["client_key"], expired)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_refuses_a_token_signed_with_another_secret(self):
        client = ObjectGenerator.create_client()
        foreign = forge("um-segredo-que-nao-e-o-da-api-1234567890", subject_key=client["client_key"])

        status, response = RequestGenerator.GET_client(client["client_key"], foreign)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_refuses_the_alg_none_attack(self):
        client = ObjectGenerator.create_client()
        unsigned = jwt.encode(
            {"subject_key": client["client_key"], "type": "client", "jti": str(uuid4()), "exp": int(time.time()) + 600},
            key=None,
            algorithm="none",
        )

        status, response = RequestGenerator.GET_client(client["client_key"], unsigned)

        assert status == 401
        assert response["code"] == "QIT003001"

    @pytest.mark.skipif(not environ.get("JWT_SECRET"), reason="precisa do JWT_SECRET no ambiente")
    def test_refuses_a_valid_signature_with_an_unknown_subject_type(self):
        client = ObjectGenerator.create_client()
        odd = forge(environ["JWT_SECRET"], subject_key=client["client_key"], type="alien")

        status, response = RequestGenerator.GET_client(client["client_key"], odd)

        assert status == 401
        assert response["code"] == "QIT003001"
