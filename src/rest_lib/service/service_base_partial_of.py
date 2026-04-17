import typing as ty

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase, EMPTY
from rest_lib.exception import ConflictException
from rest_lib.util.join_aux import JoinAux
from rest_lib.util.order_spec import PARTIAL_JOIN_ALIAS

from rest_lib.service.service_base_util import ServiceBaseUtil


@dataclass
class PartialExtensionWriteData:
    table_name: str
    relation_field: str
    related_entity_attr: str
    all_values: Dict[str, Any]
    provided_columns: Set[str]


class ServiceBasePartialOf(ServiceBaseUtil):
    def _has_partial_support(self) -> bool:
        """
        Verifica se a classe de DTO e a classe de entidade estão configuradas para uso de entidades parciais.

        Returns:
            bool: Verdadeiro se a classe de DTO e a classe de entidade possuem configuração de suporte a entidades parciais, falso caso contrário.
        """
        return (
            getattr(self._dto_class, "partial_dto_config", None) is not None
            and getattr(self._entity_class, "partial_entity_config", None) is not None
        )

    def _get_partial_join_alias(self) -> str:
        return PARTIAL_JOIN_ALIAS

    def _split_partial_fields(
        self,
        fields: Set[str],
        dto_class=None,
    ) -> Tuple[Set[str], Set[str]]:
        if fields is None:
            return (set(), set())

        if dto_class is None:
            dto_class = self._dto_class

        partial_config = getattr(dto_class, "partial_dto_config", None)
        if partial_config is None:
            return (set(fields), set())

        base_fields: Set[str] = set()
        extension_fields: Set[str] = set()

        for field in fields:
            if field in partial_config.extension_fields:
                extension_fields.add(field)
            else:
                base_fields.add(field)

        return (base_fields, extension_fields)

    def _convert_partial_fields_to_entity(
        self,
        fields: Set[str],
        dto_class=None,
    ) -> Set[str]:
        if not fields:
            return set()

        if dto_class is None:
            dto_class = self._dto_class

        entity_fields: Set[str] = set()
        for field in fields:
            try:
                entity_field = self._convert_to_entity_field(field, dto_class)
            except KeyError:
                entity_field = field
            entity_fields.add(entity_field)

        return entity_fields

    def _build_partial_exists_clause(
        self,
        joins_aux: List[JoinAux],
    ) -> ty.Optional[Tuple[str, str, str]]:
        if not self._has_partial_support():
            return None

        alias = self._get_partial_join_alias()
        if joins_aux is not None:
            for join_aux in joins_aux:
                if join_aux.alias == alias:
                    return None

        partial_config = getattr(self._dto_class, "partial_dto_config", None)
        partial_entity_config = getattr(
            self._entity_class, "partial_entity_config", None
        )

        if partial_config is None or partial_entity_config is None:
            return None

        try:
            base_field = self._convert_to_entity_field(
                partial_config.related_entity_field,
                dto_class=partial_config.parent_dto,
            )
        except KeyError:
            base_field = partial_config.related_entity_field

        relation_field = partial_config.relation_field
        table_name = partial_entity_config.extension_table_name

        if table_name is None or base_field is None or relation_field is None:
            return None

        return (table_name, base_field, relation_field)

    def _prepare_partial_save_entities(
        self,
        dto: DTOBase,
        partial_update: bool,
        is_insert: bool,
    ) -> Tuple[EntityBase | None, PartialExtensionWriteData | None]:
        if not self._has_partial_support():
            return (None, None)

        partial_config = getattr(self._dto_class, "partial_dto_config", None)
        partial_entity_config = getattr(
            self._entity_class, "partial_entity_config", None
        )

        if partial_config is None or partial_entity_config is None:
            return (None, None)

        if partial_entity_config.extension_table_name is None:
            raise ValueError(
                "Extensão parcial configurada sem 'extension_table_name' definido na entity."
            )

        # Entity da tabela base
        base_entity_class = partial_entity_config.parent_entity
        base_entity = dto.convert_to_entity(
            base_entity_class,
            partial_update,
            is_insert,
        )

        # Conversão para obter os valores da extensão
        extension_entity = dto.convert_to_entity(
            self._entity_class,
            partial_update,
            is_insert,
        )

        all_values: Dict[str, Any] = {}
        provided_columns: Set[str] = set()
        provided_fields = getattr(dto, "_provided_fields", set())

        for field in partial_config.extension_fields:
            if field not in self._dto_class.fields_map:
                continue

            dto_field = self._dto_class.fields_map[field]
            column_name = dto_field.get_entity_field_name() or field
            value = getattr(extension_entity, column_name, None)

            if value is EMPTY:
                converted_value = None
            else:
                converted_value = value

            all_values[column_name] = converted_value

            if not partial_update:
                provided_columns.add(column_name)
            elif field in provided_fields and value is not EMPTY:
                provided_columns.add(column_name)

        # Garantindo que os campos de particionamento sejam persistidos na extensão
        for partition_field in getattr(self._dto_class, "partition_fields", set()):
            dto_field = self._dto_class.fields_map.get(partition_field)
            if dto_field is None:
                continue

            column_name = dto_field.get_entity_field_name() or partition_field

            if column_name == partial_config.relation_field:
                continue

            if not hasattr(extension_entity, column_name):
                continue

            if partial_update and partition_field not in provided_fields:
                continue

            partition_value = getattr(base_entity, column_name, None)

            if partition_value is EMPTY:
                partition_value = None

            all_values[column_name] = partition_value
            provided_columns.add(column_name)

        relation_field = partial_config.relation_field
        if relation_field in all_values:
            all_values.pop(relation_field)
            if relation_field in provided_columns:
                provided_columns.remove(relation_field)

        write_data = PartialExtensionWriteData(
            table_name=partial_entity_config.extension_table_name,
            relation_field=relation_field,
            related_entity_attr=partial_config.related_entity_field,
            all_values=all_values,
            provided_columns=provided_columns,
        )

        return (base_entity, write_data)

    def _resolve_partial_relation_value(
        self,
        entity: EntityBase,
        write_data: PartialExtensionWriteData,
    ) -> Any:
        relation_attr = write_data.related_entity_attr
        relation_value = None

        if relation_attr and hasattr(entity, relation_attr):
            relation_value = getattr(entity, relation_attr)

        if relation_value is None:
            relation_value = getattr(entity, entity.get_pk_field())

        return relation_value

    def _handle_partial_extension_insert(
        self,
        entity: EntityBase,
        write_data: PartialExtensionWriteData,
    ) -> None:
        if write_data is None:
            return

        relation_value = self._resolve_partial_relation_value(entity, write_data)

        extension_payload = dict(write_data.all_values)
        extension_payload[write_data.relation_field] = relation_value

        if self._dao.partial_extension_exists(
            write_data.table_name,
            write_data.relation_field,
            relation_value,
        ):
            raise ConflictException(
                "Já existe um registro de extensão parcial associado a este identificador."
            )

        self._dao.insert_partial_extension_record(
            write_data.table_name,
            extension_payload,
        )

    def _handle_partial_extension_update(
        self,
        entity: EntityBase,
        write_data: PartialExtensionWriteData,
        partial_update: bool,
    ) -> None:
        if write_data is None:
            return

        relation_value = self._resolve_partial_relation_value(entity, write_data)

        update_payload = dict(write_data.all_values)

        if partial_update:
            update_payload = {
                column: update_payload[column]
                for column in write_data.provided_columns
                if column in update_payload
            }

        exists = self._dao.partial_extension_exists(
            write_data.table_name,
            write_data.relation_field,
            relation_value,
        )

        if not exists:
            insert_payload = dict(write_data.all_values)
            insert_payload[write_data.relation_field] = relation_value
            if not insert_payload:
                insert_payload = {write_data.relation_field: relation_value}
            self._dao.insert_partial_extension_record(
                write_data.table_name,
                insert_payload,
            )
            return

        if not update_payload:
            return

        self._dao.update_partial_extension_record(
            write_data.table_name,
            write_data.relation_field,
            relation_value,
            update_payload,
        )
