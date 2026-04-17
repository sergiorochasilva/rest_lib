import os
import typing as ty

from flask import request
from sqlalchemy.exc import IntegrityError, ProgrammingError
from typing import Callable

from rest_lib.util.json_util import json_dumps, JsonLoadException
from rest_lib.util.rest_error_util import format_json_error

from rest_lib.controller.controller_util import (
    DEFAULT_RESP_HEADERS,
    map_db_exception_to_http,
)
from rest_lib.controller.route_base import RouteBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.dto.queued_data_dto import QueuedDataDTO
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import MissingParameterException, NotFoundException
from rest_lib.injector_factory_base import NsjInjectorFactoryBase
from rest_lib.settings import get_logger


class PatchRoute(RouteBase):
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
        custom_before_update: Callable = None,
        custom_after_update: Callable = None,
        retrieve_after_partial_update: bool = False,
        custom_json_response: bool = False,
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
        self.custom_before_update = custom_before_update
        self.custom_after_update = custom_after_update
        self.retrieve_after_partial_update = retrieve_after_partial_update
        self.custom_json_response = custom_json_response

    def handle_request(
        self,
        id: str,
        query_args: dict[str, any] = None,
        body: dict[str, any] = None,
        **kwargs: ty.Any,
    ):
        """
        Processa requisicao HTTP PATCH para atualizacao parcial de entidade.

        Args:
            id: Identificador da entidade (URL).
            query_args: Query params no modo ERP SQL.
            body: Corpo da requisicao no modo ERP SQL.
            **kwargs: Filtros adicionais injetados pela rota/framework.

        Returns:
            Tupla Flask (body, status_code, headers).
        """

        try:
            # Recuperando os dados do corpo da requisição
            if os.getenv("ENV", "").lower() != "erp_sql":
                data = request.json
                args = request.args
            else:
                data = body
                args = query_args or {}

            if len(kwargs) > 0:
                data.update(kwargs)

            # Convertendo os dados para o DTO
            data = self._dto_class(
                validate_read_only=True,
                escape_validator=True,
                **data,
            )

            # Reaplicando validação apenas nos campos enviados
            data.escape_validator = False
            for field_name in getattr(data, "_provided_fields", set()):
                if field_name in data.fields_map:
                    setattr(data, field_name, getattr(data, field_name))

            # Montando os filtros de particao de dados
            partition_filters = kwargs.copy()

            for field in data.partition_fields:
                value = getattr(data, field)
                if value is None:
                    raise MissingParameterException(field)
                elif value is not None:
                    partition_filters[field] = value

            # Construindo os objetos
            service = self._get_service(self.get_injector_factory())
            retrieve_fields = (
                RouteBase.parse_fields(self._dto_class, args.get("fields"))
                if self.retrieve_after_partial_update
                else None
            )

            # Chamando o service (método insert)
            data = service.partial_update(
                dto=data,
                id=id,
                aditional_filters=partition_filters,
                custom_before_update=self.custom_before_update,
                custom_after_update=self.custom_after_update,
                retrieve_after_partial_update=self.retrieve_after_partial_update,
                custom_json_response=self.custom_json_response,
                retrieve_fields=retrieve_fields,
            )

            if data is not None:
                # Verificando se houve um enfileiramento (pelo custom_after_update)
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

                # Convertendo para o formato de dicionário
                dict_data = data.convert_to_dict(retrieve_fields)

                # Retornando a resposta da requuisição
                return (json_dumps(dict_data), 200, {**DEFAULT_RESP_HEADERS})
            else:
                # Retornando a resposta da requuisição
                return ("", 204, {**DEFAULT_RESP_HEADERS})
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
        except NotFoundException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 404, {**DEFAULT_RESP_HEADERS})
        except (IntegrityError, ProgrammingError) as e:
            # Converte erros de persistencia do banco para resposta HTTP coerente.
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
