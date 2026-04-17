from typing import Any, Dict, List, Set

from rest_lib.util.json_util import convert_to_dumps
from rest_lib.entity.entity_base import EntityBase, EMPTY
from rest_lib.entity.filter import Filter
from rest_lib.exception import NotFoundException
from rest_lib.settings import USE_SQL_RETURNING_CLAUSE

from .dao_base_insert import DAOBaseInsert

class DAOBaseUpdate(DAOBaseInsert):

    def _sql_upsert_fields(
        self,
        entity: EntityBase,
        ignore_nones: bool = False,
        sql_read_only_fields: List[str] = [],
    ) -> str:
        """
        Retorna lista com os campos para upsert, no padrão "field = excluded.field"
        """

        sql_fields = (
            entity._sql_fields
            if entity._sql_fields
            else [
                f"{k}"
                for k in entity.__dict__
                if not callable(getattr(entity, k, None)) and not k.startswith("_")
            ]
        )

        # Building SQL fields
        fields = [
            f"{k} = excluded.{k}"
            for k in entity.__dict__
            if not callable(getattr(entity, k, None))
            and not k.startswith("_")
            and (ignore_nones and getattr(entity, k) is not None or not ignore_nones)
            and k not in entity.get_const_fields()
            and k != entity.get_pk_field()
            and k not in sql_read_only_fields
        ]

        return ", ".join(fields)

    def _sql_update_fields(
        self,
        entity: EntityBase,
        ignore_nones: bool = False,
        sql_read_only_fields: List[str] = [],
        sql_no_update_fields: Set[str] = [],
    ) -> str:
        """
        Retorna lista com os campos para update, no padrão "field = :field"
        """

        sql_fields = (
            entity._sql_fields
            if entity._sql_fields
            else [
                f"{k}"
                for k in entity.__dict__
                if not callable(getattr(entity, k, None)) and not k.startswith("_")
            ]
        )

        # Building SQL fields
        if ignore_nones:
            fields = [
                f"{k} = :{k}"
                for k in sql_fields
                if k not in entity.get_const_fields()
                and k != entity.get_pk_field()
                and k not in sql_read_only_fields
                and k not in sql_no_update_fields
                and getattr(entity, k) is not EMPTY
            ]
        else:
            fields = [
                f"{k} = :{k}"
                for k in sql_fields
                if k not in entity.get_const_fields()
                and k != entity.get_pk_field()
                and k not in sql_read_only_fields
                and k not in sql_no_update_fields
            ]

        return ", ".join(fields)

    def update(
        self,
        key_field: str,
        key_value: Any,
        entity: EntityBase,
        filters: Dict[str, List[Filter]],
        partial_update: bool = False,
        sql_read_only_fields: List[str] = [],
        sql_no_update_fields: Set[str] = [],
        upsert: bool = False,
    ):
        """
        Atualiza o objeto de entidade "entity" no banco de dados
        """

        # Organizando o where dos filtros
        filters_where, filter_values_map = self._make_filters_sql(filters, True)

        # # CUIDADO PARA NÂO ATUALIZAR O QUE NÃO DEVE
        # if filters_where is None or filters_where.strip() == "":
        #     raise NotFoundException(
        #         f"{self._entity_class.__name__} não encontrado. Filtros: {filters}"
        #     )

        # Montando cláusula upsert
        if upsert:
            # NOTE: Does not support sql_no_update_fields.

            # Montando as cláusulas dos campos
            sql_fields, sql_ref_values = self._sql_insert_fields(
                entity, sql_read_only_fields
            )

            sql_upsert_fields = self._sql_upsert_fields(
                entity, partial_update, sql_read_only_fields
            )

            conflict_fields = f"{entity.get_pk_field()}{',' + ','.join(filters.keys()) if filters else ''}"

            conflict_rules = f"""
            ON CONFLICT ({conflict_fields}) DO
            UPDATE
            SET
                {sql_upsert_fields}

                """

            # Montando a query principal
            sql = f"""
            insert into {entity.get_table_name()} as t0 (

                {sql_fields}

            ) values (

                {sql_ref_values}

            )
            {conflict_rules}
            where
                true
                and t0.{key_field} = :candidate_key_value
                {filters_where}
            """
        else:

            # Montando a cláusula dos campos
            sql_fields = self._sql_update_fields(
                entity, partial_update, sql_read_only_fields,
                sql_no_update_fields
            )

            # Montando a query principal
            sql = f"""
            update {entity.get_table_name()} as t0 set

                {sql_fields}

            where
                true
                and t0.{key_field} = :candidate_key_value
                {filters_where}
            """

        # Montando as cláusulas returning
        returning_fields = entity.get_update_returning_fields()
        if (
            getattr(entity, entity.get_pk_field()) is None
            and entity.get_pk_field() not in returning_fields
        ):
            returning_fields.append(entity.get_pk_field())

        if len(returning_fields) > 0 and USE_SQL_RETURNING_CLAUSE:
            sql_returning = ", ".join(returning_fields)

            sql += "\n"
            sql += f"returning {sql_returning}"

        # Montando um dicionário com valores das propriedades
        values_map = convert_to_dumps(entity)

        # Montado o map de valores a passar no update
        kwargs = {"candidate_key_value": key_value, **values_map, **filter_values_map}

        # Realizando o update no BD
        rowcount, returning = self._db.execute(sql, **kwargs)

        if rowcount <= 0:
            raise NotFoundException(
                f"{self._entity_class.__name__} com id {values_map[self._entity_class().get_pk_field()]} não encontrado."
            )

        # Complementando o objeto com os dados de retorno
        if len(returning_fields) > 0 and USE_SQL_RETURNING_CLAUSE:
            for field in returning_fields:
                setattr(entity, field, returning[0][field])

        return entity
