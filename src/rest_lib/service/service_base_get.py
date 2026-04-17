import typing as ty

from typing import Any, Dict

from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.function_type_base import FunctionTypeBase
from rest_lib.exception import ConflictException
from rest_lib.util.fields_util import FieldsTree
from rest_lib.util.fields_util import extract_child_tree


from .service_base_retrieve import ServiceBaseRetrieve


class ServiceBaseGet(ServiceBaseRetrieve):

    def get(
        self,
        id: str,
        partition_fields: Dict[str, Any],
        fields: FieldsTree,
        expands: ty.Optional[FieldsTree] = None,
        function_params: Dict[str, Any] | None = None,
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ) -> DTOBase:

        if expands is None:
            expands = {"root": set()}

        fn_name = function_name
        # GET por função só deve ocorrer quando o nome da função
        # for informado explicitamente.
        if fn_name is not None:
            return self._get_by_function(
                id,
                partition_fields,
                fields,
                expands,
                function_params or {},
                function_object,
                function_name=fn_name,
                custom_json_response=custom_json_response,
            )

        # Resolving fields
        fields = self._resolving_fields(fields)

        if self._has_partial_support():
            base_root_fields, partial_root_fields = self._split_partial_fields(
                fields["root"]
            )
        else:
            base_root_fields = set(fields["root"])
            partial_root_fields = set()

        # Handling the fields to retrieve
        entity_fields = self._convert_to_entity_fields(base_root_fields)
        partial_join_fields = self._convert_partial_fields_to_entity(
            partial_root_fields
        )

        # Tratando dos filtros
        all_filters = {}
        if self._dto_class.fixed_filters is not None:
            all_filters.update(self._dto_class.fixed_filters)
        if partition_fields is not None:
            all_filters.update(partition_fields)

        ## Adicionando os filtros para override de dados
        self._add_overide_data_filters(all_filters)

        entity_filters = self._create_entity_filters(all_filters)

        # Resolve o campo de chave sendo utilizado
        entity_key_field, entity_id_value = self._resolve_field_key(
            id,
            partition_fields,
        )

        # Resolvendo os joins
        joins_aux = self._resolve_sql_join_fields(
            fields["root"], entity_filters, partial_join_fields
        )

        partial_exists_clause = self._build_partial_exists_clause(joins_aux)

        # Recuperando a entity
        override_data = (
            self._dto_class.data_override_group is not None
            and self._dto_class.data_override_fields is not None
        )
        entity = self._dao.get(
            entity_key_field,
            entity_id_value,
            entity_fields,
            entity_filters,
            conjunto_type=self._dto_class.conjunto_type,
            conjunto_field=self._dto_class.conjunto_field,
            joins_aux=joins_aux,
            partial_exists_clause=partial_exists_clause,
            override_data=override_data,
        )

        # NOTE: This has to happens on the entity
        if len(self._dto_class.one_to_one_fields_map) > 0:
            self._retrieve_one_to_one_fields(
                [entity],
                fields,
                expands,
                partition_fields,
            )

        # NOTE: This has to be done first so the DTOAggregator can have
        #           the same name as a field in the entity
        for k, v in self._dto_class.aggregator_fields_map.items():
            if k not in fields["root"]:
                continue
            if k in expands:
                orig_dto = self._dto_class
                self._dto_class = v.expected_type
                self._retrieve_one_to_one_fields(
                    [entity],
                    fields,
                    extract_child_tree(expands, k),
                    partition_fields,
                )
                self._dto_class = orig_dto
                pass
            setattr(entity, k, v.expected_type(entity, escape_validator=True))
            pass

        # Convertendo para DTO
        if not override_data:
            dto = self._dto_class(entity, escape_validator=True)
        else:
            # Convertendo para uma lista de DTOs
            dto_list = [self._dto_class(e, escape_validator=True) for e in entity]

            # Agrupando o resultado, de acordo com o override de dados
            dto_list = self._group_by_override_data(dto_list)

            if len(dto_list) > 1:
                raise ConflictException(
                    f"Encontrado mais de um registro do tipo {self._entity_class.__name__}, para o id {id}."
                )

            dto = dto_list[0]

        # Tratando das propriedades de lista
        if len(self._dto_class.list_fields_map) > 0:
            self._retrieve_related_lists([dto], fields, expands)

        # Tratando das propriedades de relacionamento left join
        if len(self._dto_class.left_join_fields_map) > 0:
            self._retrieve_left_join_fields(
                [dto],
                fields,
                partition_fields,
            )

        if len(self._dto_class.object_fields_map) > 0:
            self._retrieve_object_fields(
                [dto],
                fields,
                partition_fields,
            )

        return dto

    def _get_by_function(
        self,
        id: str,
        partition_fields: Dict[str, Any],
        fields: FieldsTree,
        expands: FieldsTree,
        function_params: Dict[str, Any],
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ) -> DTOBase:
        from rest_lib.exception import NotFoundException

        all_params: Dict[str, Any] = {}
        if partition_fields:
            all_params.update(partition_fields)
        all_params.update(function_params or {})

        rows: list[dict] = []
        dto_class = self._get_function_response_dto_class

        fn_name = function_name
        if not fn_name:
            raise ValueError("Nome da função GET não informado.")

        if function_object is not None:
            if isinstance(function_object, FunctionTypeBase):
                # Chamada por TYPE composto (FunctionType)
                rows = self._dao._call_function_with_type(function_object, fn_name)
            else:
                raise TypeError(
                    "function_object deve ser um FunctionTypeBase em _get_by_function."
                )
        else:
            # Chamada RAW (parâmetros simples)
            positional_values = []
            if id is not None:
                positional_values.append(id)
            rows = self._dao._call_function_raw(
                fn_name,
                positional_values,
                all_params,
            )

        if custom_json_response:
            if not rows:
                raise NotFoundException(
                    f"{self._entity_class.__name__} com id {id} não encontrado."
                )
            return rows[0]

        dtos = self._map_function_rows_to_dtos(
            rows,
            dto_class,
            operation="get",
        )

        if not dtos:
            raise NotFoundException(
                f"{self._entity_class.__name__} com id {id} não encontrado."
            )

        dto = dtos[0]
        return dto
