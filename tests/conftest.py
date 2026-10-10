from pathlib import Path
from os import path, environ

import pytest

root = Path(__file__).resolve().parents[1]

if not environ.get("APP_ENV") or environ.get("APP_ENV") in ("local", "test"):
    from dotenv import load_dotenv

    load_dotenv(path.join(str(root), ".env"))

    if environ.get("SERVER_LOCALHOST") is None:
        environ["SERVER_LOCALHOST"] = "127.0.0.1"


@pytest.fixture
def operator_token() -> str:
    """Um token de operador novo por teste.

    Nao e session-scoped de proposito: um teste que faz logout com ele
    (ou que roda depois de um DbUtils.rollback) nao pode sujar o teste
    seguinte.
    """
    from tests.utils.object_generator import ObjectGenerator

    return ObjectGenerator.operator_token()
