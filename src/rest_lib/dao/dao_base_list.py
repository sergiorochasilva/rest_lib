import re
import uuid

from typing import Dict, List, Tuple

from rest_lib.util.log_time import log_time

from rest_lib.descriptor.conjunto_type import ConjuntoType
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.filter import Filter
from rest_lib.exception import (
    AfterRecordNotFoundException,
    NotFoundException,
)
from rest_lib.util.join_aux import JoinAux
from rest_lib.util.order_spec import (
    OrderFieldSource,
    OrderFieldSpec,
)
from rest_lib.settings import get_logger

from .dao_base_search import DAOBaseSearch


class DAOBaseList(DAOBaseSearch):

    @log_time
    def list(
        self,
        after: uuid.UUID,
        limit: int,
        fields: List[str],
        order_fields: List[OrderFieldSpec] | List[str] | None,
        filters: Dict[str, List[Filter]],
        conjunto_type: ConjuntoType = None,
        conjunto_field: str = None,
        entity_key_field: str = None,
        entity_id_value: any = None,
        search_query: str = None,
        search_fields: List[str] = None,
        joins_aux: List[JoinAux] = None,
        partial_exists_clause: Tuple[str, str, str] = None,
    ) -> List[EntityBase]:
        """
        Returns a paginated entity list.
        """

        # Creating a entity instance
        entity = self._entity_class()

        raw_order_fields = order_fields
        if raw_order_fields is None:
            raw_order_fields = entity.get_default_order_fields()

        order_specs: List[OrderFieldSpec] = []
        for field in raw_order_fields:
            if isinstance(field, OrderFieldSpec):
                order_specs.append(field)
                continue

            if not isinstance(field, str):
                raise ValueError(
                    "order_fields deve ser uma lista de strings ou OrderFieldSpec."
                )

            field_clean = re.sub(
                r"\basc\b|\bdesc\b", "", field, flags=re.IGNORECASE
            ).strip()
            is_desc = bool(re.search(r"\bdesc\b", field, flags=re.IGNORECASE))
            order_specs.append(
                OrderFieldSpec(
                    column=field_clean,
                    is_desc=is_desc,
                    source=OrderFieldSource.BASE,
                    alias=None,
                )
            )

        sql_order_items: List[Tuple[str, str, bool, str]] = []
        order_fields_alias: List[str] = []
        for spec in order_specs:
            alias_resolved = self._resolve_order_alias(spec)
            param_name = self._build_order_param(alias_resolved, spec.column)
            sql_order_items.append(
                (alias_resolved, spec.column, spec.is_desc, param_name)
            )

            clause = f"{alias_resolved}.{spec.column}"
            if spec.is_desc:
                clause = f"{clause} desc"
            order_fields_alias.append(clause)

        # Resolving data to pagination
        order_map = {param: None for _, _, _, param in sql_order_items}

        if after is not None:
            try:
                if entity_key_field is None:
                    after_obj = self.get(
                        entity.get_pk_field(),
                        after,
                        fields,
                        filters.copy(),
                        conjunto_type=conjunto_type,
                        conjunto_field=conjunto_field,
                        joins_aux=joins_aux,
                        partial_exists_clause=partial_exists_clause,
                    )
                else:
                    after_obj = self.get(
                        entity_key_field,
                        entity_id_value,
                        fields,
                        filters.copy(),
                        conjunto_type=conjunto_type,
                        conjunto_field=conjunto_field,
                        joins_aux=joins_aux,
                        partial_exists_clause=partial_exists_clause,
                    )
            except NotFoundException as e:
                raise AfterRecordNotFoundException(
                    f"Identificador recebido no parâmetro after {id}, não encontrado para a entidade {self._entity_class.__name__}."
                )

            if after_obj is not None:
                for _, column, _, param_name in sql_order_items:
                    order_map[param_name] = getattr(after_obj, column, None)

        # Making default order by clause
        order_by = f"""
            {', '.join(order_fields_alias)}
        """

        # Organizando o where da paginação
        pagination_where = ""
        if after is not None:
            # Making a list of pagination condictions
            list_page_where = []
            old_specs: List[Tuple[str, str, bool, str]] = []
            for alias, column, is_desc, param_name in sql_order_items:
                # Making equals condictions
                buffer_old_fields = "true"
                for old_alias, old_column, _, old_param in old_specs:
                    buffer_old_fields += f" and {old_alias}.{old_column} = :{old_param}"

                # Making current more than condiction
                list_page_where.append(
                    f"({buffer_old_fields} and {alias}.{column} {'<' if is_desc else '>'} :{param_name})"
                )

                # Storing current field as old
                old_specs.append((alias, column, is_desc, param_name))

            # Making SQL page condiction
            pagination_where = f"""
                and (
                    false
                    or {' or '.join(list_page_where)}
                )
            """

        # Montando o filtro de search (com ilike)
        search_map, search_where = self._make_search_sql(
            search_query, search_fields, entity
        )

        # Resolvendo o join de conjuntos (se houver)
        with_conjunto = ""
        fields_conjunto = ""
        join_conjuntos = ""
        conjunto_map = {}
        if conjunto_type is not None:
            (
                join_conjuntos,
                with_conjunto,
                fields_conjunto,
                conjunto_map,
            ) = self._make_conjunto_sql(conjunto_type, entity, filters, conjunto_field)

        # Organizando o where dos filtros
        filters_where, filter_values_map = self._make_filters_sql(filters)

        # Montando a clausula dos fields vindos dos joins
        sql_join_fields, sql_join = self._make_joins_sql(joins_aux)

        if joins_aux:
            for join in joins_aux:
                for field in join.fields:
                    setattr(self._entity_class, f"{join.alias}_{field}", None)

        partial_exists_sql = ""
        if partial_exists_clause is not None:
            (
                partial_table_name,
                partial_base_field,
                partial_relation_field,
            ) = partial_exists_clause
            partial_exists_sql = f"""
            and exists (
                select 1
                from {partial_table_name} as partial_exists
                where partial_exists.{partial_relation_field} = t0.{partial_base_field}
            )
            """

        # Montando a query em si
        sql = f"""
        {with_conjunto}
        select

            {fields_conjunto}
            {self._sql_fields(fields)}
            {sql_join_fields}

        from
            {entity.get_table_name()} as t0
            {join_conjuntos}
            {sql_join}

        where
            true
            {pagination_where}
            {filters_where}
            {search_where}
            {partial_exists_sql}

        order by
            {order_by}
        """

        # Adding limit if received
        if limit is not None:
            sql += f"        limit {limit}"

        # Making the values dict
        kwargs = {**order_map, **filter_values_map, **conjunto_map, **search_map}

        # Running the SQL query
        get_logger().debug(f"[RestLib Debug] List SQL: {sql}")
        get_logger().debug(f"[RestLib Debug] List Parameters: {kwargs}")
        resp = self._db.execute_query_to_model(sql, self._entity_class, **kwargs)

        return resp
