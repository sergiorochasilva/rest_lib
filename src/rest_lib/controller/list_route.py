import os
import typing as ty

from flask import request
from typing import Callable

from rest_lib.util.json_util import json_dumps
from rest_lib.util.log_time import log_time
from rest_lib.util.pagination_util import page_body, PaginationException
from rest_lib.util.rest_error_util import format_json_error

from rest_lib.controller.controller_util import DEFAULT_RESP_HEADERS
from rest_lib.controller.route_base import RouteBase
from rest_lib.dao.dao_base import DAOBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import (
    DataOverrideParameterException,
    MissingParameterException,
)
from rest_lib.injector_factory_base import NsjInjectorFactoryBase
from rest_lib.settings import get_logger, DEFAULT_PAGE_SIZE
from rest_lib.util.fields_util import merge_fields_tree


class ListRoute(RouteBase):
    def __init__(
        self,
        url: str,
        http_method: str,
        dto_class: DTOBase,
        entity_class: EntityBase,
        injector_factory: NsjInjectorFactoryBase = NsjInjectorFactoryBase,
        service_name: str = None,
        handle_exception: Callable = None,
        list_function_type_class: type | None = None,
        list_function_name: str | None = None,
        list_function_response_dto_class: type | None = None,
        custom_json_response: bool = False,
    ):
        """
        Rota de LIST (GET sem ID).

        - ``list_function_type_class``: subclasse de
          ``ListFunctionTypeBase`` representando o TYPE de entrada da
          função PL/pgSQL de listagem. Quando informado, a chamada é
          feita via ``_call_function_with_type``. Se omitido, a listagem
          é feita via SELECT direto na tabela.
        - ``list_function_name``: nome da função PL/pgSQL para LIST por
          função (ex.: ``teste.api_classificacaofinanceiralist``).
        - ``list_function_response_dto_class``: DTO usado para mapear o
          retorno da função (fallback para ``dto_class``).
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
        self._list_function_type_class = list_function_type_class
        self._list_function_name = list_function_name
        self._list_function_response_dto_class = (
            list_function_response_dto_class or dto_class
        )
        self.custom_json_response = custom_json_response

    def _get_service(self, factory: NsjInjectorFactoryBase):
        """
        Sobrescreve o _get_service padrão para permitir configurar
        o DTO de resposta de função diretamente no construtor do Service.
        """

        if self._service_name is not None:
            return factory.get_service_by_name(self._service_name)

        from rest_lib.service.service_base import ServiceBase

        return ServiceBase(
            factory,
            DAOBase(factory.db_adapter(), self._entity_class),
            self._dto_class,
            self._entity_class,
            self._dto_response_class,
            list_function_response_dto_class=self._list_function_response_dto_class,
        )

    @log_time
    def handle_request(
        self,
        query_args: dict[str, any] = None,
        body: dict[str, any] = None,
        **kwargs: ty.Any,
    ):
        """
        Tratando requisições HTTP Get (para listar entidades, e não para recuperar pelo ID).
        """

        try:
            # Recuperando os parâmetros básicos
            if os.getenv("ENV", "").lower() != "erp_sql":
                base_url = request.base_url
                args = request.args
            else:
                base_url = ""
                args = query_args

            limit = int(args.get("limit", DEFAULT_PAGE_SIZE))
            current_after = args.get("after") or args.get("offset")

            # Tratando dos fields
            fields = args.get("fields")
            fields = RouteBase.parse_fields(self._dto_class, fields)
            url_args = (
                base_url
                + "?"
                + "&".join(
                    [
                        f"{arg}={value}"
                        for arg, value in args.items()
                        if arg not in ["limit", "after", "offset"]
                    ]
                )
            )

            expands = RouteBase.parse_expands(self._dto_class, args.get("expand"))
            merge_fields_tree(fields, expands)

            # Tratando dos filters e search_query
            filters, search_query = RouteBase.parse_filters_and_search(
                self._dto_class, args, kwargs
            )
            order_fields = RouteBase.parse_order(self._dto_class, args)

            # Tratando dos campos de data_override
            self._validade_data_override_parameters(args)

            # Construindo os objetos
            service = self._get_service(self.get_injector_factory())

            function_object = None
            if self._list_function_type_class is not None:
                function_object = RouteBase.build_function_type_from_args(
                    self._list_function_type_class,
                    filters,
                    id_value=None,
                )
            function_params = None if function_object is not None else filters

            # Chamando o service (método list)
            data = service.list(
                current_after,
                limit,
                fields,
                order_fields,
                filters,
                search_query=search_query,
                expands=expands,
                function_params=function_params,
                function_object=function_object,
                function_name=self._list_function_name,
                custom_json_response=self.custom_json_response,
            )

            if self.custom_json_response and self._list_function_name is not None:
                return (json_dumps(data), 200, {**DEFAULT_RESP_HEADERS})

            # Convertendo para o formato de dicionário (permitindo omitir campos do DTO)
            dict_data = [dto.convert_to_dict(fields, expands) for dto in data]

            # Recuperando o campo referente à chave primária do DTO
            pk_field = self._dto_class.pk_field

            # Construindo o corpo da página
            page = page_body(
                base_url=url_args,
                limit=limit,
                current_after=current_after,
                current_before=None,
                result=dict_data,
                id_field=pk_field,
            )

            # Retornando a resposta da requuisição
            return (json_dumps(page), 200, {**DEFAULT_RESP_HEADERS})
        except MissingParameterException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except DataOverrideParameterException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except PaginationException as e:
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
