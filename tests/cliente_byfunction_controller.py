from tests.cliente_byfunction_dto import ClienteByfunctionDTO
from tests.cliente_byfunction_entity import ClienteByfunctionEntity
from tests.cliente_byfunction_insert_function_type import (
    ClienteByfunctionInsertType,
)
from rest_lib.settings import application, APP_NAME, MOPE_CODE

from rest_lib.controller.list_route import ListRoute
from rest_lib.controller.post_route import PostRoute

LIST_POST_ROUTE = f"/{APP_NAME}/{MOPE_CODE}/clientes-by-function"


@application.route(LIST_POST_ROUTE, methods=["GET"])
@ListRoute(
    url=LIST_POST_ROUTE,
    http_method="GET",
    dto_class=ClienteByfunctionDTO,
    entity_class=ClienteByfunctionEntity,
)
def get_clientes_byfunction(request, response):
    return response


@application.route(LIST_POST_ROUTE, methods=["POST"])
@PostRoute(
    url=LIST_POST_ROUTE,
    http_method="POST",
    dto_class=ClienteByfunctionDTO,
    entity_class=ClienteByfunctionEntity,
    insert_function_type_class=ClienteByfunctionInsertType,
    insert_function_name="teste.api_clientenovo",
)
def post_clientes_byfunction(request, response):
    return response
