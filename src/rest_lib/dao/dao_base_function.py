import typing as ty

from rest_lib.util.json_util import convert_to_dumps

from rest_lib.dao.dao_base_save_by_function import _FunctionSQLBuilder
from rest_lib.dao.dao_base_util import DAOBaseUtil
from rest_lib.entity.function_type_base import FunctionTypeBase
from rest_lib.settings import get_logger


class DAOBaseFunction(DAOBaseUtil):
    def _call_function_with_type(
        self,
        function_object: FunctionTypeBase,
        function_name: str,
    ) -> list[dict]:
        """
        Executa uma função de banco que recebe um TYPE composto (FunctionType).
        Retorna a lista de registros (dict) gerada pela função.
        """

        function_type_class = function_object.__class__
        if not function_name:
            raise ValueError(
                f"É necessário informar o nome da função para {function_type_class.__name__}."
            )

        (
            relation_declarations,
            assignments,
            values_map,
        ) = _FunctionSQLBuilder(function_object).build()

        declarations_sql = "\n".join(
            f"    DECLARE {declaration}" for declaration in relation_declarations
        )

        assignments_sql = "\n".join(f"        {line}" for line in assignments)

        sql = f"""
        DO $DOFUNC$
            DECLARE VAR_TIPO {function_type_class.type_name};
{declarations_sql if declarations_sql else ''}
            DECLARE VAR_RETORNO JSONB;
        BEGIN
{assignments_sql}

            VAR_RETORNO = (
                SELECT coalesce(jsonb_agg(row_to_json(r)), '[]'::jsonb)
                FROM {function_name}(VAR_TIPO) r
            );
            PERFORM set_config('retorno.bloco', VAR_RETORNO::varchar, true);
        END $DOFUNC$;

        SELECT current_setting('retorno.bloco', true)::jsonb as retorno;
        """

        get_logger().debug(f"[RestLib Debug] Function SQL: {sql}")
        get_logger().debug(f"[RestLib Debug] Function Parameters: {values_map}")
        _, returning = self._db.execute_batch(sql, **values_map)

        if not returning:
            return []

        retorno = returning[0].get("retorno")
        if retorno is None:
            return []
        if isinstance(retorno, list):
            return retorno
        # Caso venha um único objeto jsonb
        return [retorno]

    def _call_function_raw(
        self,
        function_name: str,
        positional_values: list,
        named_values: dict[str, ty.Any] | None = None,
    ) -> list[dict]:
        """
        Executa uma função de banco passando parâmetros simples (sem TYPE composto).
        """
        named_values = named_values or {}

        values_map: dict[str, ty.Any] = {}
        placeholders = []

        for idx, value in enumerate(positional_values):
            placeholder = f"p_{idx}"
            placeholders.append(f":{placeholder}")
            values_map[placeholder] = convert_to_dumps(value)

        for key, value in named_values.items():
            safe_key = key.replace("-", "_")
            placeholders.append(f":{safe_key}")
            values_map[safe_key] = convert_to_dumps(value)

        args_sql = ", ".join(placeholders)
        sql = f"select * from {function_name}({args_sql});"

        returning = self._db.execute_query(sql, **values_map)

        return returning or []
