from typing import Any, Dict, List
from rest_lib.controller.route_base import RouteBase


class RequestPropertyDoc:
    def __init__(
        self,
        name: str,
        type: str,
        description: str
    ):
        self.name = name
        self.type = type
        self.description = description


class ResponsePropertyDoc(RequestPropertyDoc):
    pass


class RouteDoc:
    def __init__(
        self,
        http_method: str,
        url: str,
        description: str,
        request_body: List[RequestPropertyDoc],
        response_body: Dict[str, Any],
        response_statuses: Dict[str, str]
    ):
        self.http_method = http_method
        self.url = url
        self.description = description
        self.request_body = request_body
        self.response_body = response_body
        self.response_statuses = response_statuses


class MopeDoc:
    def __init__(
        self,
        mope_code: str,
        routes_doc: List[RouteDoc]
    ):
        self.mope_code = mope_code
        self.routes_doc = routes_doc


def generate():
    """
    Teste
    """
    routes = {}

    # Agrupando as rotas pelo código mope
    for route in RouteBase.registered_routes:
        # Identificando o mope_code e o recurso rest
        url = route.url.split('/')
        mope_code = url[0]

        # Guardando a rota em seu grupo
        mope_routes = routes.setdefault(mope_code, [])
        mope_routes.append(route)

    # Iterando as rotas, para cosntruir as documentações
    docs = []
    for mope_code, mope_routes in routes.items():
        # Criando a lista de documentações
        routes_doc = []

        # Iterando as rotas para gerar a documentação
        for route in mope_routes:
            http_method = route.http_method
            url = route.url
            description = route.function_wrapper.func.__doc__
            request_body,
            response_body,
            response_statuses

            RouteDoc(
                http_method,
                url,
                description,
                request_body,
                response_body,
                response_statuses
            )

            # Guardando a documentação
            pass

        mope_doc = MopeDoc(mope_code, routes_doc)
        docs.append(mope_doc)
