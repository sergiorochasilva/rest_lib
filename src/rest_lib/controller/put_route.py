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
from rest_lib.entity.function_type_base import UpdateFunctionTypeBase
from rest_lib.exception import (
    MissingParameterException,
    NotFoundException,
    ConflictException,
)
from rest_lib.injector_factory_base import NsjInjectorFactoryBase
from rest_lib.settings import get_logger


class PutRoute(RouteBase):
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
        retrieve_after_update: bool = False,
        custom_json_response: bool = False,
        update_function_type_class: Type[UpdateFunctionTypeBase] | None = None,
        update_function_name: str | None = None,
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
        self.retrieve_after_update = retrieve_after_update
        self.custom_json_response = custom_json_response
        self._update_function_type_class = update_function_type_class
        self._update_function_name = update_function_name

        if self._update_function_type_class is not None and not issubclass(
            self._update_function_type_class, UpdateFunctionTypeBase
        ):
            raise ValueError(
                "A classe informada em update_function_type_class deve herdar de UpdateFunctionTypeBase."
            )

    def _get_service(self, factory: NsjInjectorFactoryBase):
        """
        Sobrescreve o _get_service padrão para permitir configurar
        o UpdateFunctionType e o nome da função diretamente no Service.
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
            update_function_type_class=self._update_function_type_class,
            update_function_name=self._update_function_name,
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
        id: str = None,
        query_args: dict[str, any] = None,
        body: dict[str, any] = None,
        **kwargs: ty.Any,
    ):
        """
        Processa requisicao HTTP PUT para atualizar (ou upsert) entidade.

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
                request_data = request.json
                args = request.args
            else:
                request_data = body
                args = query_args or {}

            # Parâmetros da requisição
            is_upsert = args.get(
                "upsert", False, type=lambda value: value.lower() == "true"
            )
            retrieve_fields = (
                RouteBase.parse_fields(self._dto_class, args.get("fields"))
                if self.retrieve_after_update
                else None
            )

            if not isinstance(request_data, list):
                request_data = [request_data]

            data_pack = []
            lst_data = []
            partition_filters = None
            for item in request_data:
                if not isinstance(item, dict):
                    raise ValueError(
                        "O corpo da requisição deve conter objetos JSON válidos."
                    )

                if len(kwargs) > 0:
                    item.update(kwargs)

                # Em rotas unitárias de update, o ID da rota sempre prevalece
                # sobre qualquer ID vindo no corpo.
                if id is not None and self._dto_class.pk_field is not None:
                    item[self._dto_class.pk_field] = id

                item["generate_default_pk_value"] = False

                # Convertendo os dados para o DTO
                data = self._dto_class(**item)

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
                data = service.update(
                    dto=data,
                    id=id if id is not None else getattr(data, data.pk_field),
                    aditional_filters=partition_filters,
                    custom_before_update=self.custom_before_update,
                    custom_after_update=self.custom_after_update,
                    upsert=is_upsert,
                    function_name=self._update_function_name,
                    retrieve_after_update=self.retrieve_after_update,
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
                    lst_data.append(data.convert_to_dict(retrieve_fields))
            else:
                data = service.update_list(
                    dtos=data_pack,
                    aditional_filters=partition_filters,
                    custom_before_update=self.custom_before_update,
                    custom_after_update=self.custom_after_update,
                    upsert=is_upsert,
                    function_name=self._update_function_name,
                    retrieve_after_update=self.retrieve_after_update,
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
        except ConflictException as e:
            get_logger().warning(e)
            if self._handle_exception is not None:
                return self._handle_exception(e)
            else:
                return (format_json_error(e), 409, {**DEFAULT_RESP_HEADERS})
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
