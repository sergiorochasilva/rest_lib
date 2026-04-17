from flask import request
from typing import Any, Callable


class FunctionRouteWrapper:
    route_ref_count = {}
    func: Callable

    def __init__(self, route_obj, func: Callable):
        super().__init__()

        self.func = func
        self.route_obj = route_obj

        # Assumindo o nome da rota como o nome da classe
        route_name = route_obj.__class__.__name__

        # Resolvendo o contador de referências dessa mesma rota
        ref_count = FunctionRouteWrapper.route_ref_count.get(route_name, 0) + 1
        FunctionRouteWrapper.route_ref_count[route_name] = ref_count

        # Guardando as propriedades
        self._route_obj = route_obj
        self.__name__ = f"{route_name}_{ref_count}"

    def __call__(self, *args: Any, **kwargs: Any):

        # Retorna o resultado da chamada ao método handle_request do objeto de rota associado
        response = self._route_obj.internal_handle_request(*args, **kwargs)
        return self.func(request, response)
