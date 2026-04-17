from typing import Any, Dict

from .dao_base_util import DAOBaseUtil

class DAOBasePartialOf(DAOBaseUtil):

    def partial_extension_exists(
        self,
        table_name: str,
        relation_field: str,
        relation_value: Any,
    ) -> bool:
        sql = f"select 1 from {table_name} where {relation_field} = :relation_value limit 1"
        resp = self._db.execute_query(sql, relation_value=relation_value)
        return resp is not None and len(resp) > 0

    def insert_partial_extension_record(
        self,
        table_name: str,
        data: Dict[str, Any],
    ) -> None:
        if data is None or len(data) == 0:
            raise ValueError("Não há dados para inserir na extensão parcial.")

        columns = list(data.keys())
        params = {f"pe_{idx}": data[col] for idx, col in enumerate(columns)}
        placeholders = [f":{key}" for key in params]

        sql = (
            f"insert into {table_name} ({', '.join(columns)}) "
            f"values ({', '.join(placeholders)})"
        )

        rowcount, _ = self._db.execute(sql, **params)

        if rowcount <= 0:
            raise Exception(
                f"Erro inserindo registro na extensão parcial '{table_name}'."
            )

    def update_partial_extension_record(
        self,
        table_name: str,
        relation_field: str,
        relation_value: Any,
        data: Dict[str, Any],
    ) -> int:
        if not data:
            return 0

        set_params = {}
        set_clauses = []
        for idx, (column, value) in enumerate(data.items()):
            param_name = f"pe_set_{idx}"
            set_params[param_name] = value
            set_clauses.append(f"{column} = :{param_name}")

        sql = (
            f"update {table_name} set {', '.join(set_clauses)} "
            f"where {relation_field} = :relation_value"
        )

        params = {**set_params, "relation_value": relation_value}
        rowcount, _ = self._db.execute(sql, **params)

        return rowcount
