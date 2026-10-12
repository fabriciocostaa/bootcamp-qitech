from fastapi import Request, Response
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ClientController
from utils.schema_handler import SchemaHandler

DEFAULT_LIMIT = 10
DEFAULT_PAGE = 0


class ClientResource:

    def on_get_status_events(self, client_key: str) -> JSONResponse:
        controller = ClientController()
        client = controller.get_status_history(client_key)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_client.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = ClientController()
        client = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_by_key(self, client_key: str) -> JSONResponse:
        controller = ClientController()
        client = controller.get_by_key(client_key)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("put_client.json")
    def on_put_by_key(self, client_key: str, payload: dict) -> JSONResponse:
        controller = ClientController()
        client = controller.update_status(client_key, payload["status"])

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_202_ACCEPTED,
        )


    @SchemaHandler.validate_query_params("get_clients.json")
    def on_get_list(self, request: Request) -> JSONResponse:
        controller = ClientController()

        query_params = request.query_params

        limit = int(query_params.get("limit", DEFAULT_LIMIT))
        page = int(query_params.get("page", DEFAULT_PAGE))

        filters = {
            "status_enumerators": query_params.getlist("status"),
            "name": query_params.get("name"),
            "email": query_params.get("email"),
            "document_number": query_params.get("document_number"),
            "birthdate_from": query_params.get("birthdate_from"),
            "birthdate_to": query_params.get("birthdate_to"),
        }

        offset = page * limit
        client_page = controller.get_list(limit, offset, filters)

        page_envelope = {
            "data": client_page["client_list_dto"],
            "limit": limit,
            "page": page,
            "is_last_page": client_page["is_last_page"],
        }

        return JSONResponse(
            content=jsonable_encoder(page_envelope),
            status_code=http_status.HTTP_200_OK,
        )
