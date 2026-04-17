import os
import typing as ty

from flask import request
from sqlalchemy.exc import IntegrityError, ProgrammingError
from typing import Callable, Type

from rest_lib.util.json_util import json_dumps, JsonLoadException
from rest_lib.util.rest_error_util import format_json_error

from rest_lib.controller.controller_util import (
    DEFAULT_RESP_HEADERS,
    map_db_exception_to_http,
)
from rest_lib.controller.route_base import RouteBase
from rest_lib.dao.dao_base import DAOBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.dto.queued_data_dto import QueuedDataDTO
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import InsertFunctionTypeBase
from rest_lib.exception import (
    MissingParameterException,
    ConflictException,
)
from rest_lib.injector_factory_base import NsjInjectorFactoryBase
from rest_lib.settings import get_logger


class PostRoute(RouteBase):
    def __init__(
        self,
        url: str,
        http_method: str,
        dto_class: DTOBase,
        entity_class: EntityBase,
        dto_response_class: DTOBase = None,
        injector_factory: NsjInjectorFactoryBase = NsjInjectorFactoryBase,
        service_name: str = None,
        handle_exception: Callable = None,
        custom_before_insert: Callable = None,
        custom_after_insert: Callable = None,
        retrieve_after_insert: bool = False,
        custom_json_response: bool = False,
        insert_function_type_class: Type[InsertFunctionTypeBase] | None = None,
        insert_function_name: str | None = None,
    ):
        super().__init__(
            url=url,
            http_method=http_method,
            dto_class=dto_class,
            entity_class=entity_class,
            dto_response_class=dto_response_class,
            injector_factory=injector_factory,
            service_name=service_name,
            handle_exception=handle_exception,
        )
        self.custom_before_insert = custom_before_insert
        self.custom_after_insert = custom_after_insert
        self.retrieve_after_insert = retrieve_after_insert
        self.custom_json_response = custom_json_response
        self._insert_function_type_class = insert_function_type_class
        self._insert_function_name = insert_function_name

        if self._insert_function_type_class is not None and not issubclass(
            self._insert_function_type_class, InsertFunctionTypeBase
        ):
            raise ValueError(
                "A classe informada em insert_function_type_class deve herdar de InsertFunctionTypeBase."
            )

    def _get_service(self, factory: NsjInjectorFactoryBase):
        """
        Sobrescreve o _get_service padrão para permitir configurar
        o InsertFunctionType e o nome da função diretamente no Service.
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
            insert_function_type_class=self._insert_function_type_class,
            insert_function_name=self._insert_function_name,
        )

    def _partition_filters(self, data):
        # Montando os filtros de particao de dados
        partition_filters = {}

        for field in data.partition_fields:
            value = getattr(data, field)
            if value is None:
                raise MissingParameterException(field)
            elif value is not None:
                partition_filters[field] = value

        return partition_filters

    def handle_request(
        self,
        query_args: dict[str, any] = None,
        body: dict[str, any] = None,
        **kwargs: ty.Any,
    ):
        """
        Tratando requisições HTTP Post para inserir uma instância de uma entidade.
        """

        try:
            # Recuperando os dados do corpo da requisição
            if os.getenv("ENV", "").lower() != "erp_sql":
                request_data = request.json
            else:
                request_data = body

            if not isinstance(request_data, list):
                request_data = [request_data]

            args = (
                request.args
                if os.getenv("ENV", "").lower() != "erp_sql"
                else query_args or {}
            )
            retrieve_fields = (
                RouteBase.parse_fields(self._dto_class, args.get("fields"))
                if self.retrieve_after_insert
                else None
            )

            data_pack = []
            lst_data = []
            partition_filters = None
            for item in request_data:
                if len(kwargs) >= 0:
                    item.update(kwargs)

                # Convertendo os dados para o DTO
                data = self._dto_class(validate_read_only=True, **item)

                # Montando os filtros de particao de dados
                if partition_filters is None:
                    partition_filters = self._partition_filters(data)

                data_pack.append(data)

            if partition_filters is None:
                if len(kwargs) > 0:
                    partition_filters = kwargs.copy()
            else:
                partition_filters.update(kwargs)

            # Construindo os objetos
            service = self._get_service(self.get_injector_factory())

            if len(data_pack) == 1:
                # Chamando o service (método insert)
                data = service.insert(
                    dto=data,
                    aditional_filters=partition_filters,
                    custom_before_insert=self.custom_before_insert,
                    custom_after_insert=self.custom_after_insert,
                    retrieve_after_insert=self.retrieve_after_insert,
                    function_name=self._insert_function_name,
                    custom_json_response=self.custom_json_response,
                    retrieve_fields=retrieve_fields,
                )

                if data is not None:
                    # Verificando se houve um enfileiramento (pelo custom_after_insert)
                    if isinstance(data, QueuedDataDTO):
                        queued_data: QueuedDataDTO = data
                        resp_headers = {
                            **DEFAULT_RESP_HEADERS,
                            "Location": queued_data.status_url,
                        }
                        return ("", 202, resp_headers)

                    if self.custom_json_response and (
                        isinstance(data, dict)
                        or (
                            isinstance(data, list)
                            and (not data or not hasattr(data[0], "convert_to_dict"))
                        )
                    ):
                        return (json_dumps(data), 200, {**DEFAULT_RESP_HEADERS})

                    # Convertendo para o formato de dicionário (permitindo omitir campos do DTO)
                    lst_data.append(data.convert_to_dict(retrieve_fields))
            else:
                data = service.insert_list(
                    dtos=data_pack,
                    aditional_filters=partition_filters,
                    custom_before_insert=self.custom_before_insert,
                    custom_after_insert=self.custom_after_insert,
                    retrieve_after_insert=self.retrieve_after_insert,
                    function_name=self._insert_function_name,
                    custom_json_response=self.custom_json_response,
                    retrieve_fields=retrieve_fields,
                )

                if (
                    self.custom_json_response
                    and isinstance(data, list)
                    and (not data or not hasattr(data[0], "convert_to_dict"))
                ):
                    return (json_dumps(data), 200, {**DEFAULT_RESP_HEADERS})

                if data is not None or not len(data) > 0:
                    # Convertendo para o formato de dicionário (permitindo omitir campos do DTO)
                    lst_data = [item.convert_to_dict(retrieve_fields) for item in data]

            if len(lst_data) == 1:
                # Retornando a resposta da requisição
                return (json_dumps(lst_data[0]), 200, {**DEFAULT_RESP_HEADERS})

            if len(lst_data) > 1:
                # Retornando a resposta da requisição
                return (json_dumps(lst_data), 200, {**DEFAULT_RESP_HEADERS})

            # Retornando a resposta da requisição
            return ("", 201, {**DEFAULT_RESP_HEADERS})
        except JsonLoadException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except MissingParameterException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except ValueError as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 400, {**DEFAULT_RESP_HEADERS})
        except ConflictException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 409, {**DEFAULT_RESP_HEADERS})
        except (IntegrityError, ProgrammingError) as e:
            get_logger().warning(e)
            mapped = map_db_exception_to_http(e)
            if mapped is None:
                raise
            status_code, message = mapped
            if self._handle_exception is not None:
                return self._handle_exception(e)
            return (format_json_error(message), status_code, {**DEFAULT_RESP_HEADERS})
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
