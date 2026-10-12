from fastapi import FastAPI

from constants import check_variables
from errors import register_error_handlers
from errors.base_error import error_verification
from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
    register_auth_middleware
)
from resources import HealthCheckResource, ClientResource, CreditResource
from resources import AccountResource, AuthResource
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    register_auth_middleware(application)
    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)

    health_check_resource = HealthCheckResource()
    client_resource = ClientResource()
    account_resource = AccountResource()
    auth_resource = AuthResource()
    credit_resource = CreditResource()


    application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
    application.add_api_route(
        "/health_check",
        health_check_resource.on_get_health_check,
        methods=["GET"]
    )

    application.add_api_route(
        "/client",
        client_resource.on_post,
        methods=["POST"],
    )
    application.add_api_route(
        "/client/{client_key}",
        client_resource.on_get_by_key,
        methods=["GET"],
    )
    application.add_api_route(
        "/client/{client_key}",
        client_resource.on_put_by_key,
        methods=["PUT"],
    )

    application.add_api_route(
        "/clients",
        client_resource.on_get_list,
        methods=["GET"],
    )

    application.add_api_route(
        "/account/{account_key}/status-events",
        account_resource.on_get_status_events,
        methods=["GET"],
    )

    application.add_api_route(
        "/client/{client_key}/status-events",
        client_resource.on_get_status_events,
        methods=["GET"],
    )

    application.add_api_route(
        "/account/{account_key}/deposit",
        account_resource.on_post_deposit,
        methods=["POST"],
    )

    application.add_api_route(
        "/account/{account_key}/withdraw",
        account_resource.on_post_withdraw,
        methods=["POST"],
    )

    application.add_api_route(
        "/account/{account_key}/transfer",
        account_resource.on_post_transfer,
        methods=["POST"],
    )

    application.add_api_route(
        "/account/{account_key}/extract",
        account_resource.on_get_extract,
        methods=["GET"],
    )

    application.add_api_route(
    "/account/{account_key}",
    account_resource.on_patch_by_key,
    methods=["PATCH"],
    )

    application.add_api_route(
        "/auth/login",
        auth_resource.on_post_login,
        methods=["POST"],
    )

    application.add_api_route(
        "/auth/operator/login",
        auth_resource.on_post_operator_login, methods=["POST"]
    )


    application.add_api_route(
        "/auth/logout",
        auth_resource.on_post_logout,
        methods=["POST"],
    )

    application.add_api_route(
        "/client/{client_key}/credit",
        credit_resource.on_post,
        methods=["POST"],
    )

    application.add_api_route(
        "/client/{client_key}/credit/withdraw",
        credit_resource.on_post_withdraw,
        methods=["POST"],
    )

    application.add_api_route(
        "/client/{client_key}/invoice/pay",
        credit_resource.on_post_pay_invoice,
        methods=["POST"],
    )

    application.add_api_route

    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()
