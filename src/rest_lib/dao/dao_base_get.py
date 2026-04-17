import uuid

from typing import List, Tuple

from rest_lib.descriptor.conjunto_type import ConjuntoType
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import ConflictException, NotFoundException
from rest_lib.util.join_aux import JoinAux

from .dao_base_conjuntos import DAOBaseConjuntos


class DAOBaseGet(DAOBaseConjuntos):

    def get(
        self,
        key_field: str,
        id: uuid.UUID,
        fields: List[str] = None,
        filters=None,
        conjunto_type: ConjuntoType = None,
        conjunto_field: str = None,
        joins_aux: List[JoinAux] = None,
        override_data: bool = False,
        partial_exists_clause: Tuple[str, str, str] = None,
    ) -> EntityBase:
        """
        Returns an entity instance by its ID.
        """

        # Creating a entity instance
        entity = self._entity_class()

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

        # Building query
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
            t0.{key_field} = :id
            {filters_where}
            {partial_exists_sql}
        limit 10
        """
        values = {"id": id}
        values.update(filter_values_map)
        values.update(conjunto_map)

        # Running query
        resp = self._db.execute_query_to_model(sql, self._entity_class, **values)

        # Checking if ID was found
        if len(resp) <= 0:
            raise NotFoundException(
                f"{self._entity_class.__name__} com id {id} não encontrado."
            )

        # Verificando se foi encontrado mais de um registro para o ID passado
        if not override_data and len(resp) > 1:
            raise ConflictException(
                f"Encontrado mais de um registro do tipo {self._entity_class.__name__}, para o id {id}."
            )

        if not override_data:
            return resp[0]
        else:
            return resp
