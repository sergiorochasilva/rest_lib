import os
import typing as ty

from flask import request
from typing import Callable

from rest_lib.util.json_util import json_dumps
from rest_lib.util.rest_error_util import format_json_error, format_error_body

from rest_lib.controller.controller_util import DEFAULT_RESP_HEADERS
from rest_lib.controller.route_base import RouteBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import (
    MissingParameterException,
    NotFoundException,
)
from rest_lib.injector_factory_base import NsjInjectorFactoryBase
from rest_lib.settings import get_logger


class DeleteRoute(RouteBase):
    def __init__(
        self,
        url: str,
        http_method: str,
        dto_class: DTOBase,
        entity_class: EntityBase,
        injector_factory: NsjInjectorFactoryBase = NsjInjectorFactoryBase,
        service_name: str = None,
        handle_exception: Callable = None,
        custom_before_delete: Callable = None,
        delete_function_type_class: type | None = None,
        delete_function_name: str | None = None,
        custom_json_response: bool = False,
    ):
        """
        Rota de DELETE.

        - ``delete_function_type_class``: subclasse de
          ``DeleteFunctionTypeBase`` representando o TYPE de entrada da
          função PL/pgSQL de exclusão. Quando informado, a chamada é
          feita via ``_call_function_with_type``. Se omitido, a exclusão
          é feita direto na tabela.
        - ``delete_function_name``: nome da função PL/pgSQL para DELETE
          por função (ex.: ``teste.api_classificacaofinanceiraexcluir``).
        - ``custom_before_delete``: callback opcional executado antes do
          delete.
        """
        super().__init__(
            url=url,
            http_method=http_method,
            dto_class=dto_class,
            entity_class=entity_class,
            dto_response_class=None,
            injector_factory=injector_factory,
            service_name=service_name,
            handle_exception=handle_exception,
        )
        self.custom_before_delete = custom_before_delete
        self._delete_function_type_class = delete_function_type_class
        self._delete_function_name = delete_function_name
        self.custom_json_response = custom_json_response

    def _partition_filters(self, args):
        partition_filters = {}
        # Tratando campos de particionamento
        for field in self._dto_class.partition_fields:
            value = args.get(field)
            if value is None:
                raise MissingParameterException(field)
            partition_filters[field] = value

        return partition_filters

    def _exception_to_http(self, exception: Exception):
        if isinstance(exception, MissingParameterException):
            return 400, exception

        if isinstance(exception, NotFoundException):
            return 404, exception

        return 500, exception

    def _multi_status_response(
        self,
        request_data: list,
        delete_return: dict,
    ) -> dict:
        """
        Constrói a resposta para api multi-status
        """
        _return_mapping = {}
        _global_status = (
            "OK"
            if len(delete_return) == 0
            else "ERROR" if len(delete_return) == len(request_data) else "MULTI-STATUS"
        )
        for _id in request_data:
            if _id in delete_return:
                _return_mapping[_id] = self._exception_to_http(delete_return[_id])
            else:
                _return_mapping[_id] = 204, None

        _response = {
            "global_status": _global_status,
            "response": [
                {
                    "status": _http_code,
                    "id": _id,
                    "body": {},
                    "error": next(iter(format_error_body(f"{_ex}")), {}) if _ex else {},
                }
                for _id, (_http_code, _ex) in _return_mapping.items()
            ],
        }
        return _response

    def handle_request(
        self,
        id: str = None,
        query_args: dict[str, any] = None,
        body: dict[str, any] = None,
        **kwargs: ty.Any,
    ):
        """
        Tratando requisições HTTP Delete para excluir uma instância de uma entidade.
        """

        try:
            # Recuperando os parâmetros básicos
            if os.getenv("ENV", "").lower() != "erp_sql":
                args = request.args
            else:
                args = query_args

            # Recuperando os dados do corpo da requisição
            if request.data:
                request_data = request.json

                if not isinstance(request_data, list):
                    request_data = [request_data]

            partition_filters = self._partition_filters(args)
            partition_filters.update(kwargs)

            # Construindo os objetos
            service = self._get_service(self.get_injector_factory())

            if id is not None:
                function_object = None
                if self._delete_function_type_class is not None:
                    params = dict(args)
                    params.update(partition_filters)
                    function_object = RouteBase.build_function_type_from_args(
                        self._delete_function_type_class,
                        params,
                        id_value=id,
                    )
                custom_response = service.delete(
                    id,
                    partition_filters,
                    custom_before_delete=self.custom_before_delete,
                    function_params=None if function_object is not None else args,
                    function_object=function_object,
                    function_name=self._delete_function_name,
                    custom_json_response=self.custom_json_response,
                )

                if self.custom_json_response and custom_response is not None:
                    return (
                        json_dumps(custom_response),
                        200,
                        {**DEFAULT_RESP_HEADERS},
                    )

                # Retornando a resposta da requisição
                return ("", 204, {**DEFAULT_RESP_HEADERS})
            else:

                request_data = list(
                    map(
                        lambda item: item["id"] if isinstance(item, dict) else item,
                        request_data,
                    )
                )

                _delete_return = {}
                for _id in request_data:
                    try:
                        function_object = None
                        if self._delete_function_type_class is not None:
                            params = dict(args)
                            params.update(partition_filters)
                            function_object = RouteBase.build_function_type_from_args(
                                self._delete_function_type_class,
                                params,
                                id_value=_id,
                            )
                        service.delete(
                            _id,
                            partition_filters,
                            custom_before_delete=self.custom_before_delete,
                            function_params=(
                                None if function_object is not None else args
                            ),
                            function_object=function_object,
                            function_name=self._delete_function_name,
                        )
                    except Exception as e:
                        _delete_return[_id] = e

                _response = self._multi_status_response(request_data, _delete_return)

                return (json_dumps(_response), 207, {**DEFAULT_RESP_HEADERS})

        except MissingParameterException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except NotFoundException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 404, {**DEFAULT_RESP_HEADERS})
        except ValueError as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except Exception as e:
            get_logger().exception(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (
                    format_json_error(f"Erro desconhecido: {e}"),
                    500,
                    {**DEFAULT_RESP_HEADERS},
                )
