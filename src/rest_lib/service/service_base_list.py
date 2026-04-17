import re
import uuid
import typing as ty

from typing import Any, Dict, List, Set

from rest_lib.util.log_time import log_time_context

from rest_lib.descriptor.dto_aggregator import DTOAggregator
from rest_lib.descriptor.dto_left_join_field import EntityRelationOwner
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.function_type_base import FunctionTypeBase
from rest_lib.util.fields_util import FieldsTree, extract_child_tree
from rest_lib.util.order_spec import (
    OrderFieldSpec,
    OrderFieldSource,
)

from .service_base_retrieve import ServiceBaseRetrieve


class ServiceBaseList(ServiceBaseRetrieve):
    """
    Extensão do ServiceBase focada em listagem e busca textual.

    Esta classe concentra o fluxo de listagem com paginação, ordenação,
    suporte a partial DTO e construção de regras de busca em campos
    relacionais (incluindo modo ``exists``).
    """

    def filter_list(self, filters: Dict[str, Any]):
        """
        Atalho para executar listagem apenas com filtros.

        Args:
            filters (Dict[str, Any]): Dicionário de filtros em formato DTO.

        Returns:
            List[DTOBase]: Lista de DTOs resultantes da filtragem.
        """
        return self.list(
            None,
            None,
            {"root": set()},
            None,
            filters,
        )

    def _build_relation_search_specs(
        self,
        relation_name: str,
        related_dto_class,
        related_entity_class,
        relation_alias: str,
        relation_parent_field: str,
        relation_child_field: str,
        seen_specs: Set[tuple[str, str, str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Monta especificações de busca para campos de entidades relacionadas.

        Args:
            relation_name (str): Nome do relacionamento no DTO raiz.
            related_dto_class: Classe DTO da entidade relacionada.
            related_entity_class: Classe Entity da entidade relacionada.
            relation_alias (str): Alias SQL base do relacionamento.
            relation_parent_field (str): Campo da entidade principal usado na relação.
            relation_child_field (str): Campo da entidade filha usado na relação.
            seen_specs (Set[tuple[str, str, str, str]]): Estrutura para evitar duplicidade.

        Returns:
            List[Dict[str, Any]]: Lista de especificações de campo para busca
            (campos simples e joins SQL adicionais), no formato esperado por DAO.
        """
        specs: List[Dict[str, Any]] = []
        related_entity = related_entity_class()
        relation_table = related_entity.get_table_name()
        child_search_fields = getattr(related_dto_class, "search_fields", set()) or set()

        for child_search_field in child_search_fields:
            if child_search_field not in related_dto_class.fields_map:
                continue

            child_entity_field = self._convert_to_entity_field(
                child_search_field,
                dto_class=related_dto_class,
            )

            if child_entity_field not in related_entity.fields_map:
                continue

            dedupe_key = (
                relation_name,
                relation_parent_field,
                relation_child_field,
                child_entity_field,
            )
            if dedupe_key in seen_specs:
                continue
            seen_specs.add(dedupe_key)

            specs.append(
                {
                    "field": child_entity_field,
                    "entity_class": related_entity_class,
                    "relation_mode": "exists",
                    "relation_table": relation_table,
                    "relation_alias": relation_alias,
                    "relation_parent_field": relation_parent_field,
                    "relation_child_field": relation_child_field,
                }
            )

        for sql_field_name, sql_join_field in related_dto_class.sql_join_fields_map.items():
            if sql_join_field.dto_type is None or sql_join_field.entity_type is None:
                continue

            if not getattr(sql_join_field, "search", True):
                continue

            join_dto_class = sql_join_field.dto_type
            join_entity_class = sql_join_field.entity_type
            join_entity = join_entity_class()

            if sql_join_field.related_dto_field not in join_dto_class.fields_map:
                continue

            join_field_entity_name = self._convert_to_entity_field(
                sql_join_field.related_dto_field,
                dto_class=join_dto_class,
            )
            if join_field_entity_name not in join_entity.fields_map:
                continue

            join_alias = self._build_list_filter_alias(
                f"{relation_name}_{sql_field_name}_search"
            )

            if sql_join_field.entity_relation_owner == EntityRelationOwner.SELF:
                if sql_join_field.relation_field in related_dto_class.fields_map:
                    join_self_field = self._convert_to_entity_field(
                        sql_join_field.relation_field,
                        dto_class=related_dto_class,
                    )
                else:
                    join_self_field = sql_join_field.relation_field
                join_other_field = join_entity.get_pk_field()
            else:
                join_self_field = related_entity.get_pk_field()
                if sql_join_field.relation_field not in join_dto_class.fields_map:
                    continue
                join_other_field = self._convert_to_entity_field(
                    sql_join_field.relation_field,
                    dto_class=join_dto_class,
                )

            dedupe_key = (
                relation_name,
                relation_parent_field,
                relation_child_field,
                f"{join_alias}.{join_field_entity_name}",
            )
            if dedupe_key in seen_specs:
                continue
            seen_specs.add(dedupe_key)

            specs.append(
                {
                    "field": join_field_entity_name,
                    "table_alias": join_alias,
                    "entity_class": join_entity_class,
                    "relation_mode": "exists",
                    "relation_table": relation_table,
                    "relation_alias": relation_alias,
                    "relation_parent_field": relation_parent_field,
                    "relation_child_field": relation_child_field,
                    "relation_join_sql": (
                        f"{sql_join_field.join_type} join {join_entity.get_table_name()} "
                        f"as {join_alias} on ({relation_alias}.{join_self_field} = "
                        f"{join_alias}.{join_other_field})"
                    ),
                }
            )

        return specs

    def _build_search_fields(self) -> List[Any] | None:
        """
        Constrói a lista final de campos usados no parâmetro ``search``.

        Inclui campos de busca do DTO principal e também campos de
        relacionamentos 1x1 e 1xN configurados como pesquisáveis.

        Returns:
            List[Any] | None: Lista de campos/especificações para busca.
            Retorna ``None`` quando não houver campos pesquisáveis.
        """
        search_fields: List[Any] = []

        if self._dto_class.search_fields is not None:
            base_search_fields, _ = self._split_partial_fields(
                self._dto_class.search_fields
            )
            if base_search_fields:
                search_fields.extend(self._convert_to_entity_fields(base_search_fields))

        seen_specs: Set[tuple[str, str, str, str]] = set()

        for relation_name, oto_field in self._dto_class.one_to_one_fields_map.items():
            if oto_field.entity_relation_owner != EntityRelationOwner.SELF:
                continue
            if oto_field.expected_type is None or oto_field.entity_type is None:
                continue

            search_fields.extend(
                self._build_relation_search_specs(
                    relation_name=relation_name,
                    related_dto_class=oto_field.expected_type,
                    related_entity_class=oto_field.entity_type,
                    relation_alias=self._build_one_to_one_filter_alias(relation_name),
                    relation_parent_field=oto_field.entity_field,
                    relation_child_field=oto_field.relation_field,
                    seen_specs=seen_specs,
                )
            )

        for relation_name, list_field in self._dto_class.list_fields_map.items():
            if list_field.service_name is not None or list_field.entity_type is None:
                continue

            relation_key_field = list_field.relation_key_field or self._dto_class.pk_field
            if relation_key_field is None:
                continue

            relation_parent_field = self._convert_to_entity_field(relation_key_field)
            relation_child_field = list_field.related_entity_field

            search_fields.extend(
                self._build_relation_search_specs(
                    relation_name=relation_name,
                    related_dto_class=list_field.dto_type,
                    related_entity_class=list_field.entity_type,
                    relation_alias=self._build_list_filter_alias(relation_name),
                    relation_parent_field=relation_parent_field,
                    relation_child_field=relation_child_field,
                    seen_specs=seen_specs,
                )
            )

        if len(search_fields) <= 0:
            return None

        return search_fields

    def list(
        self,
        after: uuid.UUID,
        limit: int,
        fields: FieldsTree,
        order_fields: List[str],
        filters: Dict[str, Any],
        search_query: str = None,
        return_hidden_fields: set[str] = None,
        expands: ty.Optional[FieldsTree] = None,
        function_params: Dict[str, Any] | None = None,
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ) -> List[DTOBase]:
        fn_name = function_name
        # LIST por função só deve ocorrer quando o nome da função
        # for informado explicitamente.
        if fn_name is not None:
            return self._list_by_function(
                fields,
                expands or {"root": set()},
                function_params or {},
                function_object,
                function_name=fn_name,
                custom_json_response=custom_json_response,
            )
        # Resolving fields
        fields = self._resolving_fields(fields)

        has_partial = self._has_partial_support()
        partial_config = getattr(self._dto_class, "partial_dto_config", None)

        base_root_fields: Set[str] = set(fields["root"])
        partial_root_fields: Set[str] = set()
        partial_join_fields_entity: Set[str] = set()
        extension_entity_fields: Set[str] = set()

        if has_partial and partial_config is not None:
            base_root_fields, partial_root_fields = self._split_partial_fields(
                fields["root"]
            )
            partial_join_fields_entity |= self._convert_partial_fields_to_entity(
                partial_root_fields
            )
            extension_entity_fields = self._convert_partial_fields_to_entity(
                partial_config.extension_fields
            )

        base_hidden_fields = None
        if return_hidden_fields is not None:
            hidden_base_candidates = set(return_hidden_fields)
            if has_partial and extension_entity_fields:
                partial_hidden_fields = {
                    field
                    for field in hidden_base_candidates
                    if field in extension_entity_fields
                }
                if partial_hidden_fields:
                    partial_join_fields_entity |= partial_hidden_fields
                hidden_base_candidates -= partial_hidden_fields

            base_hidden_fields = (
                hidden_base_candidates if len(hidden_base_candidates) > 0 else None
            )

        if expands is None:
            expands = {"root": set()}

        entity_fields = self._convert_to_entity_fields(
            base_root_fields, return_hidden_fields=base_hidden_fields
        )

        # Handling order fields
        order_field_specs: List[OrderFieldSpec] | None = None
        if order_fields is not None:
            order_field_specs = []
            ordered_dto_fields: Set[str] = set()
            for field in order_fields:
                aux = re.sub(
                    r"\basc\b|\bdesc\b", "", field, flags=re.IGNORECASE
                ).strip()
                is_desc = bool(re.search(r"\bdesc\b", field, flags=re.IGNORECASE))
                ordered_dto_fields.add(aux)

                entity_field_name = self._convert_to_entity_field(aux)
                source = OrderFieldSource.BASE

                if (
                    has_partial
                    and partial_config is not None
                    and aux in partial_config.extension_fields
                ):
                    source = OrderFieldSource.PARTIAL_EXTENSION
                    partial_join_fields_entity.add(entity_field_name)

                order_field_specs.append(
                    OrderFieldSpec(
                        column=entity_field_name,
                        is_desc=is_desc,
                        source=source,
                        alias=None,
                    )
                )

            # Garante ordenação determinística para paginação:
            # se PK não vier no parâmetro order, adiciona como último campo ASC.
            pk_field = self._dto_class.pk_field
            if pk_field not in ordered_dto_fields:
                pk_entity_field = self._convert_to_entity_field(pk_field)
                pk_source = OrderFieldSource.BASE

                if (
                    has_partial
                    and partial_config is not None
                    and pk_field in partial_config.extension_fields
                ):
                    pk_source = OrderFieldSource.PARTIAL_EXTENSION
                    partial_join_fields_entity.add(pk_entity_field)

                order_field_specs.append(
                    OrderFieldSpec(
                        column=pk_entity_field,
                        is_desc=False,
                        source=pk_source,
                        alias=None,
                    )
                )

        # Tratando dos filtros
        all_filters = {}
        if self._dto_class.fixed_filters is not None:
            all_filters.update(self._dto_class.fixed_filters)
        if filters is not None:
            all_filters.update(filters)

        ## Adicionando os filtros para override de dados
        self._add_overide_data_filters(all_filters)

        entity_filters = self._create_entity_filters(all_filters)

        # Tratando dos campos a serem enviados ao DAO para uso do search (se necessário)
        search_fields = self._build_search_fields()

        # Resolve o campo de chave sendo utilizado
        entity_key_field, entity_id_value = (None, None)
        if after is not None:
            entity_key_field, entity_id_value = self._resolve_field_key(
                after,
                filters,
            )

        # Resolvendo os joins
        joins_aux = self._resolve_sql_join_fields(
            fields["root"], entity_filters, partial_join_fields_entity
        )

        partial_exists_clause = self._build_partial_exists_clause(joins_aux)

        # Retrieving from DAO
        entity_list = self._dao.list(
            after,
            limit,
            entity_fields,
            order_field_specs,
            entity_filters,
            conjunto_type=self._dto_class.conjunto_type,
            conjunto_field=self._dto_class.conjunto_field,
            entity_key_field=entity_key_field,
            entity_id_value=entity_id_value,
            search_query=search_query,
            search_fields=search_fields,
            joins_aux=joins_aux,
            partial_exists_clause=partial_exists_clause,
        )

        agg_field_map: ty.Dict[str, DTOAggregator] = {
            k: v
            for k, v in self._dto_class.aggregator_fields_map.items()
            if k in fields["root"]
        }

        # NOTE: This has to be done before it's converted to DTO, because after
        #           the `setattr` in this function WILL not work.
        if len(self._dto_class.one_to_one_fields_map) > 0:
            self._retrieve_one_to_one_fields(
                entity_list,
                fields,
                expands,
                filters,
            )

        # NOTE: Doing this here to expand all of the entity_list in one go
        for k, v in agg_field_map.items():
            if k not in expands:
                continue
            orig_dto = self._dto_class
            self._dto_class = v.expected_type
            self._retrieve_one_to_one_fields(
                entity_list,
                fields,
                extract_child_tree(expands, k),
                filters,
            )
            self._dto_class = orig_dto
            pass

        # Convertendo para uma lista de DTOs
        with log_time_context(
            f"Convertendo entities para lista de DTOs {self._dto_class}"
        ):
            dto_list = []
            for entity in entity_list:
                # NOTE: This has to be done first so the DTOAggregator can have
                #           the same name as a field in the entity
                for k, v in agg_field_map.items():
                    setattr(entity, k, v.expected_type(entity, escape_validator=True))
                    pass

                with log_time_context("Convertendo um único DTO"):
                    dto = self._dto_class(entity, escape_validator=True)  # type: ignore

                    # FIXME GAMBIARRA! A ideia aqui foi recuperar propriedades diretamente da Entity
                    # para o DTO, pois os PropertiesDescriptors de Relacionamento estavam usando, erradamente,
                    # o nome da Entity, e não do DTO.
                    # A solução retrocompatível foi levar essas informações para o DTO.
                    # Próximo passo é criar novos descritores e depreciar os antigos.
                    result_hf: dict[str, any] = {}
                    if return_hidden_fields:
                        for hf in return_hidden_fields:
                            value = getattr(entity, hf)
                            result_hf[hf] = value
                    setattr(dto, "return_hidden_fields", result_hf)
                dto_list.append(dto)
                pass

        # Agrupando o resultado, de acordo com o override de dados
        dto_list = self._group_by_override_data(dto_list)

        # Retrieving related lists
        if len(self._dto_class.list_fields_map) > 0:
            self._retrieve_related_lists(dto_list, fields, expands)

        # Tratando das propriedades de relacionamento left join
        # TODO Verificar se está certo passar os filtros como campos de partição
        if len(self._dto_class.left_join_fields_map) > 0:
            self._retrieve_left_join_fields(
                dto_list,
                fields,
                filters,
            )

        if len(self._dto_class.object_fields_map) > 0:
            self._retrieve_object_fields(
                dto_list,
                fields,
                filters,
            )

        # Returning
        return dto_list

    def _list_by_function(
        self,
        fields: FieldsTree,
        expands: FieldsTree,
        function_params: Dict[str, Any],
        function_object=None,
        function_name: str | None = None,
        custom_json_response: bool = False,
    ) -> List[DTOBase]:
        params: Dict[str, Any] = dict(function_params or {})
        dto_class = self._list_function_response_dto_class

        fn_name = function_name
        if not fn_name:
            raise ValueError("Nome da função LIST não informado.")

        if function_object is not None:
            if isinstance(function_object, FunctionTypeBase):
                rows = self._dao._call_function_with_type(function_object, fn_name)
            else:
                raise TypeError(
                    "function_object deve ser um FunctionTypeBase em _list_by_function."
                )
        else:
            rows = self._dao._call_function_raw(
                fn_name,
                [],
                params,
            )

        if custom_json_response:
            return rows or []

        return self._map_function_rows_to_dtos(
            rows,
            dto_class,
            operation="list",
        )
