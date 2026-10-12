import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))

SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

REVENUE_ACCOUNT_KEY = os.environ.get("REVENUE_ACCOUNT_KEY")

TRANSFER_FEE_PERCENTAGE = float(os.environ.get("TRANSFER_FEE_PERCENTAGE", "0.02"))

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "60"))

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

BANKSLIP_API_URL = os.environ.get("BANKSLIP_API_URL", "http://localhost:8080")
BANKSLIP_API_INTERNAL_TOKEN = os.environ.get("BANKSLIP_API_INTERNAL_TOKEN", "default_token")

BANKSLIP_API_TIMEOUT = int(os.environ.get("BANKSLIP_API_TIMEOUT", "5"))

BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

AUTH_BYPASS_ENDPOINTS = [
    "/auth/login",
    "/client",
    "/auth/operator/login",
]

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}. "
            "Rodando com 'docker compose up' elas já vêm preenchidas. "
            "Fora do Docker, copie o .env.example para .env."
        )
