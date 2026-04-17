import typing as ty

from rest_lib.util.db_adapter2 import DBAdapter2

from rest_lib.dao.dao_base import DAOBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)
from rest_lib.injector_factory_base import NsjInjectorFactoryBase

from .service_base_delete import ServiceBaseDelete
from .service_base_get import ServiceBaseGet
from .service_base_insert import ServiceBaseInsert
from .service_base_save_by_function import ServiceBaseSaveByFunction
from .service_base_list import ServiceBaseList
from .service_base_partial_update import ServiceBasePartialUpdate
from .service_base_update import ServiceBaseUpdate


class ServiceBase(
    ServiceBaseSaveByFunction,
    ServiceBasePartialUpdate,
    ServiceBaseUpdate,
    ServiceBaseInsert,
    ServiceBaseDelete,
    ServiceBaseList,
    ServiceBaseGet,
):
    _dao: DAOBase
    _dto_class: ty.Type[DTOBase]

    def __init__(
        self,
        injector_factory: NsjInjectorFactoryBase,
        dao: DAOBase,
        dto_class: ty.Type[DTOBase],
        entity_class: ty.Type[EntityBase],
        dto_post_response_class: DTOBase = None,
        insert_function_type_class: ty.Optional[ty.Type[InsertFunctionTypeBase]] = None,
        update_function_type_class: ty.Optional[ty.Type[UpdateFunctionTypeBase]] = None,
        get_function_name: str | None = None,
        list_function_name: str | None = None,
        delete_function_name: str | None = None,
        get_function_response_dto_class: ty.Optional[ty.Type[DTOBase]] = None,
        list_function_response_dto_class: ty.Optional[ty.Type[DTOBase]] = None,
        insert_function_name: str | None = None,
        update_function_name: str | None = None,
    ):
        self._injector_factory = injector_factory
        self._dao = dao
        self._dto_class = dto_class
        self._entity_class = entity_class
        self._dto_post_response_class = dto_post_response_class
        self._created_by_property = "criado_por"
        self._updated_by_property = "atualizado_por"
        self._insert_function_type_class = None
        self._update_function_type_class = None
        self._get_function_name = get_function_name
        self._list_function_name = list_function_name
        self._delete_function_name = delete_function_name
        self._insert_function_name = insert_function_name
        self._update_function_name = update_function_name
        self._get_function_response_dto_class = (
            get_function_response_dto_class or dto_class
        )
        self._list_function_response_dto_class = (
            list_function_response_dto_class or dto_class
        )
        self.set_insert_function_type_class(insert_function_type_class)
        self.set_update_function_type_class(update_function_type_class)

    @staticmethod
    def construtor1(
        db_adapter: DBAdapter2,
        dao: DAOBase,
        dto_class: ty.Type[DTOBase],
        entity_class: ty.Type[EntityBase],
        dto_post_response_class: DTOBase = None,
        insert_function_type_class: ty.Optional[ty.Type[InsertFunctionTypeBase]] = None,
        update_function_type_class: ty.Optional[ty.Type[UpdateFunctionTypeBase]] = None,
        get_function_name: str | None = None,
        list_function_name: str | None = None,
        delete_function_name: str | None = None,
        insert_function_name: str | None = None,
        update_function_name: str | None = None,
    ):
        """
        Esse construtor alternativo, evita a necessidade de passar um InjectorFactory,
        pois esse só é usado (internamente) para recuperar um db_adapter.

        Foi feito para não gerar breaking change de imediato (a ideia porém é, no futuro,
        gerar um breaking change).
        """

        class FakeInjectorFactory:
            def db_adapter(self):
                return db_adapter

        return ServiceBase(
            FakeInjectorFactory(),
            dao,
            dto_class,
            entity_class,
            dto_post_response_class,
            insert_function_type_class,
            update_function_type_class,
            get_function_name,
            list_function_name,
            delete_function_name,
            insert_function_name,
            update_function_name,
        )

    def _extract_params_from_dto(self, dto: DTOBase) -> dict[str, ty.Any]:
        """
        Extrai um dicionário de parâmetros a partir de um DTO já instanciado,
        considerando apenas os campos declarados em fields_map.
        """
        dto_class = dto.__class__
        fields_map = getattr(dto_class, "fields_map", {}) or {}
        result: dict[str, ty.Any] = {}
        for field_name in fields_map.keys():
            value = getattr(dto, field_name, None)
            if value is not None:
                result[field_name] = value
        return result

    def _map_function_rows_to_dtos(
        self,
        rows: list[dict],
        dto_class: ty.Type[DTOBase],
        operation: str | None = None,
    ):
        if rows is None:
            return []
        dto_fields_map = getattr(dto_class, "fields_map", {}) or {}

        dtos: list[DTOBase] = []
        for row in rows:
            dto_kwargs: dict[str, ty.Any] = {}

            # Para GET/LIST, o contrato é:
            # - o nome da coluna no retorno SEMPRE é igual a:
            #   - o valor de get_function_field, se configurado; ou
            #   - o nome do campo no DTO (descriptor.name), quando get_function_field é None.
            if operation in ("get", "list"):
                for dto_field_name, descriptor in dto_fields_map.items():
                    source_field_name = descriptor.get_function_field_name(operation)
                    dto_kwargs[dto_field_name] = row.get(source_field_name)
            else:
                dto_kwargs = self._map_generic_row_to_dto_kwargs(
                    row,
                    dto_class,
                    operation=operation,
                )

            dto_instance = dto_class(escape_validator=True, **dto_kwargs)
            dtos.append(dto_instance)

        return dtos

    def _map_generic_row_to_dto_kwargs(
        self,
        row: dict[str, ty.Any],
        dto_class: ty.Type[DTOBase],
        operation: str | None = None,
    ) -> dict[str, ty.Any]:
        """
        Mapeamento genérico de um row para kwargs de DTO.

        - Começa assumindo que as chaves do row já correspondem ao DTO.
        - Em seguida, faz um fallback procurando, no row, os nomes esperados
          pelo tipo de retorno (DTO), usando os descritores do DTO.
        """
        dto_kwargs: dict[str, ty.Any] = dict(row)

        dto_fields_map = getattr(dto_class, "fields_map", {}) or {}
        op = operation or ""

        for dto_field_name, descriptor in dto_fields_map.items():
            if dto_kwargs.get(dto_field_name) is not None:
                continue

            for candidate in (
                dto_field_name,
                descriptor.get_entity_field_name(),
                descriptor.get_function_field_name(op),
            ):
                if candidate and candidate in row and row[candidate] is not None:
                    dto_kwargs[dto_field_name] = row[candidate]
                    break

        return dto_kwargs
