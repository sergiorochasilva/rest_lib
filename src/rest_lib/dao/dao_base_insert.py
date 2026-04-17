from typing import List

from rest_lib.util.json_util import convert_to_dumps
from rest_lib.entity.entity_base import EntityBase
from rest_lib.settings import DATABASE_DRIVER, USE_SQL_RETURNING_CLAUSE

from .dao_base_save_by_function import DAOBaseSaveByFunction


class DAOBaseInsert(DAOBaseSaveByFunction):

    def _sql_insert_fields(
        self, entity: EntityBase, sql_read_only_fields: List[str] = []
    ) -> str:
        """
        Retorna uma tupla com duas partes: (sql_fields, sql_ref_values), onde:
        - sql_fields: Lista de campos a inserir no insert
        - sql_ref_values: Lista das referências aos campos, a inserir no insert (parte values)
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
            f"{k}"
            for k in sql_fields
            if k not in sql_read_only_fields or getattr(entity, k, None) is not None
        ]
        ref_values = [
            f":{k}"
            for k in sql_fields
            if k not in sql_read_only_fields or getattr(entity, k, None) is not None
        ]

        return (", ".join(fields), ", ".join(ref_values))

    def insert(self, entity: EntityBase, sql_read_only_fields: List[str] = []):
        """
        Insere o objeto de entidade "entity" no banco de dados
        """

        # Montando as cláusulas dos campos
        sql_fields, sql_ref_values = self._sql_insert_fields(
            entity, sql_read_only_fields
        )

        # Montando a query principal
        sql = f"""
        insert into {entity.get_table_name()} (

            {sql_fields}

        ) values (

            {sql_ref_values}

        )
        """

        # Montando as cláusulas returning
        returning_fields = entity.get_insert_returning_fields()
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

        # Realizando o insert no BD
        rowcount, returning = self._db.execute(sql, **values_map)

        if rowcount <= 0:
            raise Exception(
                f"Erro inserindo {entity.__class__.__name__} no banco de dados"
            )

        # Complementando o objeto com os dados de retorno
        if len(returning_fields) > 0 and USE_SQL_RETURNING_CLAUSE:
            for field in returning_fields:
                setattr(entity, field, returning[0][field])
        elif (
            getattr(entity, entity.get_pk_field()) is None
            and DATABASE_DRIVER.upper() == "MYSQL"
        ):
            last_insert_id = self._db.get_single_result("select last_insert_id()")
            if last_insert_id is not None:
                setattr(entity, entity.get_pk_field(), last_insert_id)

        return entity
