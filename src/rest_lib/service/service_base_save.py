import copy
from typing import Any, Callable, Dict, List, Set

from flask import g

from rest_lib.dao.dao_base import DAOBase
from rest_lib.dto.after_insert_update_data import AfterInsertUpdateData
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.filter import Filter
from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.exception import (
    ConflictException,
    DTOListFieldConfigException,
)
from rest_lib.service.service_base_partial_of import (
    ServiceBasePartialOf,
    PartialExtensionWriteData,
)
from rest_lib.util.fields_util import FieldsTree


class ServiceBaseSave(ServiceBasePartialOf):
    def _save(
        self,
        insert: bool,
        dto: DTOBase,
        manage_transaction: bool,
        partial_update: bool,
        relation_field_map: Dict[str, Any] = None,
        id: Any = None,
        aditional_filters: Dict[str, Any] = None,
        custom_before_insert: Callable = None,
        custom_before_update: Callable = None,
        custom_after_insert: Callable = None,
        custom_after_update: Callable = None,
        upsert: bool = False,
        retrieve_after_insert: bool = False,
        function_name: str | None = None,
        custom_json_response: bool = False,
        retrieve_fields: FieldsTree | None = None,
    ) -> DTOBase:
        try:
            received_dto = dto
            custom_response = None

            self.fill_auto_increment_fields(insert, dto)

            if manage_transaction:
                self._dao.begin()

            old_dto = None
            if not insert and not upsert:
                old_dto = self._retrieve_old_dto(dto, id, aditional_filters)
                setattr(dto, dto.pk_field, getattr(old_dto, dto.pk_field))

            if not insert and upsert:
                old_dto = dto

            if custom_before_insert:
                received_dto = copy.deepcopy(dto)
                dto = custom_before_insert(self._dao._db, dto)

            if custom_before_update:
                if received_dto == dto:
                    received_dto = copy.deepcopy(dto)
                dto = custom_before_update(self._dao._db, old_dto, dto)

            partial_write_data: PartialExtensionWriteData | None = None
            if self._has_partial_support():
                entity, partial_write_data = self._prepare_partial_save_entities(
                    dto,
                    partial_update,
                    insert,
                )
            else:
                entity = dto.convert_to_entity(
                    self._entity_class,
                    partial_update,
                    insert,
                )

            if id is None:
                id = getattr(entity, entity.get_pk_field())

            entity_pk_field = self._entity_class().get_pk_field()
            if getattr(entity, entity_pk_field) is None and insert:
                setattr(entity, entity_pk_field, id)

            if relation_field_map is not None:
                for entity_field, value in relation_field_map.items():
                    if hasattr(entity, entity_field):
                        setattr(entity, entity_field, value)
                        if entity_field not in entity._sql_fields:
                            entity._sql_fields.append(entity_field)

            if (insert and hasattr(entity, self._created_by_property)) or (
                hasattr(entity, self._updated_by_property)
            ):
                if g and hasattr(g, "profile") and g.profile is not None:
                    auth_type_is_api_key = g.profile["authentication_type"] == "api_key"
                    user = g.profile["email"]
                    if insert and hasattr(entity, self._created_by_property):
                        if not auth_type_is_api_key:
                            setattr(entity, self._created_by_property, user)
                        else:
                            value = getattr(entity, self._created_by_property)
                            if value is None or value == "":
                                raise ValueError(
                                    f"É necessário preencher o campo '{self._created_by_property}'."
                                )
                    if hasattr(entity, self._updated_by_property):
                        if not auth_type_is_api_key:
                            setattr(entity, self._updated_by_property, user)
                        else:
                            value = getattr(entity, self._updated_by_property)
                            if value is None or value == "":
                                raise ValueError(
                                    f"É necessário preencher o campo '{self._updated_by_property}'"
                                )

            if aditional_filters is not None:
                aditional_entity_filters = self._create_entity_filters(
                    aditional_filters
                )
            else:
                aditional_entity_filters = {}

            for unique in self._dto_class.uniques:
                unique = self._dto_class.uniques[unique]
                self._check_unique(
                    dto,
                    entity,
                    aditional_entity_filters,
                    unique,
                    old_dto,
                )

            if insert:
                if self.entity_exists(entity, aditional_entity_filters):
                    raise ConflictException(
                        f"Já existe um registro no banco com o identificador '{getattr(entity, entity_pk_field)}'"
                    )

                ################################################
                # DAO.INSERT (ou DAO.INSERT_BY_FUNCTION)
                ################################################
                if self._insert_function_type_class is None:
                    entity = self._dao.insert(entity, dto.sql_read_only_fields)
                else:
                    insert_function_object = self._build_insert_function_type_object(
                        dto
                    )
                    custom_response = self._dao.insert_by_function(
                        insert_function_object,
                        function_name=function_name,
                        custom_json_response=custom_json_response,
                    )

                if partial_write_data is not None:
                    self._handle_partial_extension_insert(entity, partial_write_data)

                if self._dto_class.conjunto_type is not None:
                    conjunto_field_value = getattr(dto, self._dto_class.conjunto_field)

                    aditional_filters[self._dto_class.conjunto_field] = (
                        conjunto_field_value
                    )

                    self._dao.insert_relacionamento_conjunto(
                        id, conjunto_field_value, self._dto_class.conjunto_type
                    )
            else:
                if self._update_function_type_class is not None and upsert:
                    raise ValueError(
                        "update_by_function não suporta operações com upsert."
                    )

                if self._update_function_type_class is None:
                    entity = self._dao.update(
                        entity.get_pk_field(),
                        getattr(old_dto, dto.pk_field),
                        entity,
                        aditional_entity_filters,
                        partial_update,
                        dto.sql_read_only_fields,
                        dto.sql_no_update_fields,
                        upsert,
                    )
                else:
                    update_function_object = self._build_update_function_type_object(
                        dto
                    )
                    custom_response = self._dao.update_by_function(
                        update_function_object,
                        function_name=function_name,
                        custom_json_response=custom_json_response,
                    )

                if partial_write_data is not None:
                    self._handle_partial_extension_update(
                        entity,
                        partial_write_data,
                        partial_update,
                    )

            if (
                self._dto_post_response_class is not None
                and not retrieve_after_insert
                and not custom_json_response
            ):
                response_dto = self._dto_post_response_class(
                    entity, escape_validator=True
                )
            else:
                response_dto = None

            if len(self._dto_class.list_fields_map) > 0:
                self._save_related_lists(
                    insert, dto, entity, partial_update, response_dto, aditional_filters
                )

            if custom_after_insert is not None or custom_after_update is not None:
                new_dto = self._dto_class(entity, escape_validator=True)

                for list_field in dto.list_fields_map:
                    setattr(new_dto, list_field, getattr(dto, list_field))

                if (
                    self._dto_class.conjunto_field is not None
                    and getattr(new_dto, self._dto_class.conjunto_field) is None
                ):
                    value_conjunto = getattr(dto, self._dto_class.conjunto_field)
                    setattr(new_dto, self._dto_class.conjunto_field, value_conjunto)

            after_data = AfterInsertUpdateData()
            after_data.received_dto = received_dto

            custom_data = None
            if insert:
                if custom_after_insert is not None:
                    custom_data = custom_after_insert(
                        self._dao._db, new_dto, after_data
                    )
            else:
                if custom_after_update is not None:
                    custom_data = custom_after_update(
                        self._dao._db, old_dto, new_dto, after_data
                    )

            if retrieve_after_insert and not custom_json_response:
                response_dto = self.get(id, aditional_filters, retrieve_fields)

            if custom_data is not None:
                if isinstance(custom_data, dict):
                    if response_dto is not None:
                        for key in custom_data:
                            setattr(response_dto, key, custom_data[key])
                    else:
                        response_dto = custom_data
                else:
                    if response_dto is not None:
                        pass
                    else:
                        response_dto = custom_data

            if custom_json_response and custom_response is not None:
                return custom_response

            return response_dto
        except:
            if manage_transaction:
                self._dao.rollback()
            raise
        finally:
            if manage_transaction:
                self._dao.commit()

    def fill_auto_increment_fields(self, insert, dto):
        if insert:
            auto_increment_fields = getattr(self._dto_class, "auto_increment_fields")

            for field_key in auto_increment_fields:
                field = self._dto_class.fields_map[field_key]

                if dto.__dict__.get(field.name, None):
                    continue

                if field.auto_increment.db_managed:
                    continue

                group_fields = set(field.auto_increment.group)
                for partition_field in dto.partition_fields:
                    if partition_field not in group_fields:
                        group_fields.add(partition_field)
                group_fields = list(group_fields)
                group_fields.sort()

                group_values = []
                for group_field in group_fields:
                    group_values.append(str(getattr(dto, group_field, "----")))

                next_value = self._dao.next_val(
                    sequence_base_name=field.auto_increment.sequence_name,
                    group_fields=group_values,
                    start_value=field.auto_increment.start_value,
                )

                obj_values = {}
                for f in dto.fields_map:
                    obj_values[f] = getattr(dto, f)

                value = field.auto_increment.template.format(
                    **obj_values, seq=next_value
                )

                if field.expected_type is int:
                    setattr(dto, field.name, int(value))
                else:
                    setattr(dto, field.name, value)

    def _retrieve_old_dto(self, dto, id, aditional_filters):
        fields = self._make_fields_from_dto(dto)
        get_filters = (
            copy.deepcopy(aditional_filters) if aditional_filters is not None else {}
        )

        if (
            self._dto_class.conjunto_field is not None
            and self._dto_class.conjunto_field not in get_filters
        ):
            get_filters[self._dto_class.conjunto_field] = getattr(
                dto, self._dto_class.conjunto_field
            )

        for pt_field in dto.partition_fields:
            pt_value = getattr(dto, pt_field, None)
            if pt_value is not None:
                get_filters[pt_field] = pt_value

        old_dto = self.get(id, get_filters, fields)

        if (
            self._dto_class.conjunto_field is not None
            and getattr(old_dto, self._dto_class.conjunto_field) is None
        ):
            value_conjunto = getattr(dto, self._dto_class.conjunto_field)
            setattr(old_dto, self._dto_class.conjunto_field, value_conjunto)
        return old_dto

    def _save_related_lists(
        self,
        insert: bool,
        dto: DTOBase,
        entity: EntityBase,
        partial_update: bool,
        response_dto: DTOBase,
        aditional_filters: Dict[str, Any] = None,
    ):
        # TODO Controlar profundidade?!
        from .service_base import ServiceBase

        for master_dto_field, list_field in self._dto_class.list_fields_map.items():
            response_list = []

            detail_list = getattr(dto, master_dto_field)

            if detail_list is None:
                continue

            if (
                insert
                and self._insert_function_type_class is not None
                and getattr(list_field, "insert_function_type", None) is not None
            ):
                continue

            detail_dao = DAOBase(
                self._injector_factory.db_adapter(), list_field.entity_type
            )

            if list_field.service_name is not None:
                detail_service = self._injector_factory.get_service_by_name(
                    list_field.service_name
                )
            else:
                detail_service = ServiceBase(
                    self._injector_factory,
                    detail_dao,
                    list_field.dto_type,
                    list_field.entity_type,
                    list_field.dto_post_response_type,
                )

            relation_key_field = entity.get_pk_field()
            if list_field.relation_key_field is not None:
                relation_key_field = dto.get_entity_field_name(
                    list_field.relation_key_field
                )

            relation_key_value = getattr(entity, relation_key_field)

            relation_field_map = {
                list_field.related_entity_field: relation_key_value,
            }

            old_detail_ids = None
            if not insert:
                relation_condiction = Filter(FilterOperator.EQUALS, relation_key_value)

                relation_filter = {
                    list_field.related_entity_field: [relation_condiction]
                }

                for field in self._dto_class.partition_fields:
                    if field in list_field.dto_type.partition_fields:
                        relation_filter[field] = [
                            Filter(FilterOperator.EQUALS, getattr(dto, field))
                        ]

                old_detail_ids = detail_dao.list_ids(relation_filter)

            detail_upsert_list = []

            for detail_dto in detail_list:
                detail_pk_field = detail_dto.__class__.pk_field
                detail_pk = getattr(detail_dto, detail_pk_field)

                is_detail_insert = True
                if old_detail_ids is not None and detail_pk in old_detail_ids:
                    is_detail_insert = False
                    old_detail_ids.remove(detail_pk)

                if self._dto_class.pk_field is None:
                    raise DTOListFieldConfigException(
                        f"PK field not found in class: {self._dto_class}"
                    )

                if self._dto_class.pk_field not in dto.__dict__:
                    raise DTOListFieldConfigException(
                        f"PK field not found in DTO: {self._dto_class}"
                    )

                detail_upsert_list.append(
                    {
                        "is_detail_insert": is_detail_insert,
                        "detail_dto": detail_dto,
                        "detail_pk": detail_pk,
                    }
                )

            if (
                not partial_update
                and old_detail_ids is not None
                and len(old_detail_ids) > 0
            ):
                for old_id in old_detail_ids:
                    detail_service.delete(old_id, aditional_filters)

            for item in detail_upsert_list:
                response_detail_dto = detail_service._save(
                    item["is_detail_insert"],
                    item["detail_dto"],
                    False,
                    partial_update if not item["is_detail_insert"] else False,
                    relation_field_map,
                    item["detail_pk"],
                    aditional_filters=aditional_filters,
                )

                response_list.append(response_detail_dto)

            if (
                response_dto is not None
                and master_dto_field in response_dto.list_fields_map
                and list_field.dto_post_response_type is not None
            ):
                setattr(response_dto, master_dto_field, response_list)

    def _check_unique(
        self,
        dto: DTOBase,
        entity: EntityBase,
        entity_filters: Dict[str, List[Filter]],
        unique: Set[str],
        old_dto: DTOBase,
    ):
        unique_filter = {}
        for field in unique:
            value = getattr(dto, field)
            if value is None:
                return
            unique_filter[field] = value

        unique_entity_filters = self._create_entity_filters(unique_filter)

        if entity.get_pk_field() in unique_entity_filters:
            del unique_entity_filters[entity.get_pk_field()]

        if len(unique_entity_filters) <= 0:
            return

        entity_filters = {**entity_filters, **unique_entity_filters}

        filters_pk = entity_filters.setdefault(entity.get_pk_field(), [])
        filters_pk.append(
            Filter(
                FilterOperator.DIFFERENT,
                (
                    getattr(old_dto, dto.pk_field)
                    if old_dto is not None
                    else getattr(dto, dto.pk_field)
                ),
            )
        )

        try:
            encontrados = self._dao.list(
                None,
                1,
                [entity.get_pk_field()],
                None,
                entity_filters,
            )

            if len(encontrados) >= 1:
                raise ConflictException(
                    f"Restrição de unicidade violada para a unique: {unique}"
                )
        except NotFoundException:
            return
