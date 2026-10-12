import time
from os import environ
from uuid import uuid4

import jwt
import pytest

from tests.utils import ObjectGenerator, RequestGenerator


AUTHENTICATION_ERROR = {
    "title": "Invalid Credentials",
    "description": "Document number or password is incorrect.",
    "translation": "CPF ou senha incorretos.",
    "code": "QIT003001",
}

LOGIN_ROUTES = ["/auth/login", "/auth/operator/login"]


@pytest.mark.parametrize("route", LOGIN_ROUTES)
@pytest.mark.parametrize("payload", [
    {},
    {"password": "senha-errada-123"},
    {"document_number": "390.533.447-05"},
    {"document_number": None, "password": "senha-errada-123"},
    {"document_number": "abc", "password": "senha-errada-123"},
    {"document_number": "390.533.447-05", "password": 12345678},
    {"document_number": "390.533.447-05", "password": "curta"},
    {"document_number": "390.533.447-05", "password": "a" * 256},
    {"document_number": "390.533.447-05", "password": "senha-errada-123", "extra": 1},
    [],
    None,
])
def test_login_validation_does_not_disclose_the_invalid_field(route, payload):
    response = RequestGenerator.send_raw(
        "POST", route, payload=payload, headers=RequestGenerator.build_headers()
    )

    assert response.response_status == 401
    assert response.response_json == AUTHENTICATION_ERROR


@pytest.mark.parametrize("route", LOGIN_ROUTES)
def test_login_with_malformed_json_returns_the_same_authentication_error(route):
    response = RequestGenerator.send_raw(
        "POST", route, data="isto nao e json",
        headers={**RequestGenerator.build_headers(), "Content-Type": "application/json"},
    )

    assert response.response_status == 401
    assert response.response_json == AUTHENTICATION_ERROR


@pytest.mark.parametrize("route", LOGIN_ROUTES)
@pytest.mark.parametrize("internal_token", [None, "token-incorreto"])
def test_login_with_missing_or_incorrect_internal_token_returns_the_same_error(route, internal_token):
    response = RequestGenerator.send_raw(
        "POST", route,
        payload={"document_number": "390.533.447-05", "password": "senha-errada-123"},
        headers=RequestGenerator.build_headers(internal_token=internal_token),
    )

    assert response.response_status == 401
    assert response.response_json == AUTHENTICATION_ERROR


@pytest.mark.parametrize("route", LOGIN_ROUTES)
def test_unknown_login_credentials_return_the_complete_generic_response(route):
    response = RequestGenerator.send_raw(
        "POST", route,
        payload={"document_number": "390.533.447-05", "password": "senha-errada-123"},
        headers=RequestGenerator.build_headers(),
    )

    assert response.response_status == 401
    assert response.response_json == AUTHENTICATION_ERROR


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer ", "Bearer isto.nao.e-jwt"])
def test_protected_route_does_not_disclose_why_authentication_failed(authorization):
    response = RequestGenerator.send_raw(
        "GET", "/clients", headers=RequestGenerator.build_headers(authorization=authorization)
    )

    assert response.response_status == 401
    assert response.response_json == AUTHENTICATION_ERROR


@pytest.mark.parametrize("missing_claim", ["exp", "jti", "subject_key", "type"])
def test_signed_token_with_a_missing_claim_returns_the_same_authentication_error(missing_claim):
    payload = {
        "subject_key": str(uuid4()), "type": "client", "jti": str(uuid4()),
        "exp": int(time.time()) + 600,
    }
    del payload[missing_claim]
    token = jwt.encode(payload, environ["JWT_SECRET"], algorithm="HS256")

    status, response = RequestGenerator.POST_logout(token)

    assert status == 401
    assert response == AUTHENTICATION_ERROR


@pytest.mark.parametrize("claim,value", [
    ("jti", ""),
    ("jti", None),
    ("jti", []),
    ("jti", "\x00"),
    ("jti", "k" * 37),
    ("jti", "\ud800"),
    ("subject_key", ""),
    ("subject_key", None),
    ("subject_key", {}),
    ("subject_key", "\x00"),
    ("subject_key", "s" * 37),
    ("type", "alien"),
    ("type", []),
    ("exp", str(int(time.time()) + 600)),
    ("exp", float("inf")),
    ("exp", float("nan")),
    ("exp", 10 ** 100),
])
def test_signed_token_with_an_invalid_claim_returns_401_instead_of_a_server_error(claim, value):
    payload = {
        "subject_key": str(uuid4()), "type": "client", "jti": str(uuid4()),
        "exp": int(time.time()) + 600,
    }
    payload[claim] = value
    token = jwt.encode(payload, environ["JWT_SECRET"], algorithm="HS256")

    status, response = RequestGenerator.POST_logout(token)

    assert status == 401
    assert response == AUTHENTICATION_ERROR


def test_expired_and_revoked_tokens_return_the_same_error():
    client, token = ObjectGenerator.create_authenticated_client()
    payload = {
        "subject_key": client["client_key"], "type": "client", "jti": str(uuid4()),
        "exp": int(time.time()) - 10,
    }
    expired = jwt.encode(payload, environ["JWT_SECRET"], algorithm="HS256")
    status, expired_response = RequestGenerator.GET_client(client["client_key"], expired)
    assert status == 401
    assert expired_response == AUTHENTICATION_ERROR

    status, _ = RequestGenerator.POST_logout(token)
    assert status == 200
    status, revoked_response = RequestGenerator.GET_client(client["client_key"], token)
    assert status == 401
    assert revoked_response == AUTHENTICATION_ERROR
