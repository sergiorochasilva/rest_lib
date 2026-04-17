from tests.classificacao_financeira_dto import ClassificacaoFinanceiraDTO
from tests.classificacao_financeira_entity import ClassificacaoFinanceiraEntity
from tests.classificacao_financeira_function_types import (
    ClassificacaoFinanceiraInsertType,
    ClassificacaoFinanceiraUpdateType,
    ClassificacaoFinanceiraListType,
    ClassificacaoFinanceiraGetType,
    ClassificacaoFinanceiraDeleteType,
)
from rest_lib.settings import application, APP_NAME, MOPE_CODE

from rest_lib.controller.list_route import ListRoute
from rest_lib.controller.post_route import PostRoute
from rest_lib.controller.put_route import PutRoute
from rest_lib.controller.get_route import GetRoute
from rest_lib.controller.delete_route import DeleteRoute

LIST_POST_ROUTE = f"/{APP_NAME}/{MOPE_CODE}/classificacoes-financeiras"
GET_PUT_ROUTE = f"/{APP_NAME}/{MOPE_CODE}/classificacoes-financeiras/<id>"


@application.route(LIST_POST_ROUTE, methods=["GET"])
@ListRoute(
    url=LIST_POST_ROUTE,
    http_method="GET",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    list_function_type_class=ClassificacaoFinanceiraListType,
    list_function_name="teste.api_classificacaofinanceiralist",
)
def get_classificacoes_financeiras(request, response):
    return response


@application.route(LIST_POST_ROUTE, methods=["POST"])
@PostRoute(
    url=LIST_POST_ROUTE,
    http_method="POST",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    insert_function_type_class=ClassificacaoFinanceiraInsertType,
    insert_function_name="teste.api_classificacaofinanceiranovo",
)
def post_classificacoes_financeiras(request, response):
    return response


@application.route(GET_PUT_ROUTE, methods=["PUT"])
@PutRoute(
    url=GET_PUT_ROUTE,
    http_method="PUT",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    update_function_type_class=ClassificacaoFinanceiraUpdateType,
    update_function_name="teste.api_classificacaofinanceiraalterar",
)
def put_classificacoes_financeiras(request, response):
    return response


@application.route(GET_PUT_ROUTE, methods=["GET"])
@GetRoute(
    url=GET_PUT_ROUTE,
    http_method="GET",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    get_function_type_class=ClassificacaoFinanceiraGetType,
    get_function_name="teste.api_classificacaofinanceiraget",
)
def get_classificacao_financeira(request, response):
    return response


@application.route(GET_PUT_ROUTE, methods=["DELETE"])
@DeleteRoute(
    url=GET_PUT_ROUTE,
    http_method="DELETE",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    delete_function_type_class=ClassificacaoFinanceiraDeleteType,
    delete_function_name="teste.api_classificacaofinanceiraexcluir",
)
def delete_classificacao_financeira(request, response):
    return response


@application.route(f"{LIST_POST_ROUTE}2", methods=["POST"])
@PostRoute(
    url=f"{LIST_POST_ROUTE}2",
    http_method="POST",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    insert_function_type_class=ClassificacaoFinanceiraInsertType,
    insert_function_name="teste.api_classificacaofinanceiranovo",
    retrieve_after_insert=True,
)
def post_classificacoes_financeiras2(request, response):
    return response


@application.route(f"{LIST_POST_ROUTE}2/<id>", methods=["PUT"])
@PutRoute(
    url=f"{LIST_POST_ROUTE}2/<id>",
    http_method="PUT",
    dto_class=ClassificacaoFinanceiraDTO,
    entity_class=ClassificacaoFinanceiraEntity,
    update_function_type_class=ClassificacaoFinanceiraUpdateType,
    update_function_name="teste.api_classificacaofinanceiraalterar",
    retrieve_after_update=True,
)
def put_classificacoes_financeiras2(request, response):
    return response
