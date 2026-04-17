import uuid

from sqlparams import SQLParams
from typing import List, Optional, Tuple

from rest_lib.util.log_time import log_time_context
from rest_lib.util.sql_utils import SQLUtils


class DBAdapter2:

    def __init__(self, db_connection):
        self._db = db_connection
        self._transaction = None

    def begin(self):
        if self._transaction is None:
            self._transaction = self._db.begin()

    def commit(self):
        if self._transaction is not None:
            self._transaction.commit()
            self._transaction = None

    def rollback(self):
        if self._transaction is not None:
            self._transaction.rollback()
            self._transaction = None

    def in_transaction(self):
        return self._transaction is not None

    def execute(self, sql: str, **kwargs) -> Tuple[int, Optional[list]]:
        """
        Executando uma instrução sql, com ou sem retorno.
        É obrigatório a passagem de uma conexão de banco no argumento self._db.

        Retorna o número de linhas afetadas pela instrução e o retorno esperado se houver, como uma tupla.
        O retorno é feito em forma de uma lista (list), com elementos do tipo dict (onde cada chave é igual ao
        nome do campo correspondente).
        """
        cur = None
        try:
            cur = self._execute(sql, **kwargs)

            if "returning" in sql.lower():
                rs = cur.fetchall()
                returning = [dict(rec.items()) for rec in rs]
            else:
                returning = None

            return (cur.rowcount, returning)
        finally:
            if cur is not None:
                cur.close()

    def execute_query_to_model(self, sql: str, model_class: object, **kwargs) -> list:
        """
        Executando uma instrução sql com retorno.
        O retorno é feito em forma de uma lista (list), com elementos do tipo passado pelo parâmetro
        "model_class".
        É importante destacar que para cada coluna do retorno, será procurado um atributo no model_class
        com mesmo nome, para setar o valor. Se este não for encontrado, a coluna do retorno é ignorada.
        """

        result = []
        cur = None
        try:
            cur = self._execute(sql, **kwargs)
            rs = cur.fetchall()

            for rec in rs:
                model = model_class()

                i = 0
                with log_time_context(f"Populando objeto de Modelo {model_class}"):
                    for column in cur.keys():
                        if hasattr(model, column):
                            setattr(model, column, rec[i])

                        i += 1

                result.append(model)

        finally:
            if cur is not None:
                cur.close()

        return result

    def execute_query(self, sql: str, **kwargs) -> list:
        """
        Executando uma instrução sql com retorno.
        O retorno é feito em forma de uma lista (list), com elementos do tipo dict (onde cada chave é igual ao
        nome do campo correspondente).
        """
        cur = None
        try:
            cur = self._execute(sql, **kwargs)
            rs = cur.fetchall()

            return [dict(rec.items()) for rec in rs]
        finally:
            if cur is not None:
                cur.close()

    def execute_query_first_result(self, sql: str, **kwargs) -> list:
        """
        Executando uma instrução sql com retorno.
        O retorno é feito em forma de um dict (onde cada chave é igual ao nome do campo correspondente).

        Apenas o primeiro registro é retornado (os demais serão descartados, se houverem).
        Caso não haja registros correspondentes a query, retorna None.
        """
        cur = None
        try:
            cur = self._execute(sql, **kwargs)
            rs = cur.fetchall()

            results = [dict(rec.items()) for rec in rs]

            if len(results) <= 0:
                return None
            else:
                return results[0]
        finally:
            if cur is not None:
                cur.close()

    def execute_query_first_result_to_model(
        self, sql: str, model_class: object, **kwargs
    ) -> "model_class":
        """
        Executando uma instrução sql com retorno.
        O retorno é feito em forma de um objeto do tipo passado pelo parâmetro "model_class".
        É importante destacar que para cada coluna do retorno, será procurado um atributo no model_class
        com mesmo nome, para setar o valor. Se este não for encontrado, a coluna do retorno é ignorada.
        """

        result = None
        cur = None
        try:
            cur = self._execute(sql, **kwargs)
            rs = cur.fetchone()

            if len(rs) > 0:
                model = model_class()

                i = 0
                for column in cur.keys():
                    if hasattr(model, column):
                        setattr(model, column, rs[i])

                    i += 1

                result = model

        finally:
            if cur is not None:
                cur.close()

        return result

    def get_single_result(self, sql: str, **kwargs):
        """
        Executa uma instrução SQL para a qual se espera um único retorno (com tipo primitivo). Exemplo:
        select 1+1
        Se não houver retorno, retorna None.
        """
        cur = None
        try:
            cur = self._execute(sql, **kwargs)
            return cur.scalar()
        finally:
            if cur is not None:
                cur.close()

    def _check_type(self, parameter):
        if isinstance(parameter, uuid.UUID):
            return str(parameter)
        else:
            return parameter

    def _execute(self, sql: str, **kwargs):

        new_transaction = not self.in_transaction()

        try:
            if new_transaction:
                self.begin()

            if not kwargs:
                return self._db.execute(sql)

            pars = {key: self._check_type(kwargs[key]) for key in kwargs}
            sql2, pars2 = SQLParams("named", "format").format(sql, pars)
            return self._db.execute(sql2, self._normalize_execute_params(pars2))
        except:
            if new_transaction:
                self.rollback()
            raise

        finally:
            if new_transaction:
                self.commit()

    @staticmethod
    def _normalize_execute_params(params):
        """
        SQLAlchemy 1.4+ interpreta uma list plana como executemany.
        Para execução única, o binding precisa ser tuple.
        """
        if params is None:
            return None

        if isinstance(params, list):
            if len(params) == 0:
                return tuple()

            first = params[0]
            if isinstance(first, (list, tuple, dict)):
                return params

            return tuple(params)

        return params

    def execute_query_from_file(self, query_file_path, **kwargs):
        with open(query_file_path, "r") as f:
            sql = f.read()
        return self.execute_query(sql, **kwargs)

    def execute_batch(self, sql: str, **kwargs) -> Tuple[int, List[dict]]:
        """
        Executa instruções SQL que contenham mais de um statement.
        Retorna uma tupla contendo:
        - número de linhas retornadas pelo último statement
        - lista de dicionários com os dados retornados pelo último statement
        """
        new_transaction = not self.in_transaction()
        cursor = None

        try:
            if new_transaction:
                self.begin()

            sql_to_run = (
                SQLUtils.binding_args(sql, kwargs) if kwargs is not None else sql
            )

            raw_connection = self._unwrap_db_connection()

            if hasattr(raw_connection, "execute_simple"):
                context = raw_connection.execute_simple(sql_to_run)
                rows = self._context_rows_to_dict(context)
                return len(rows), rows

            cursor = raw_connection.cursor()
            cursor.execute(sql_to_run)
            rows = self._cursor_rows_to_dict(cursor)
            return len(rows), rows

        except:
            if new_transaction:
                self.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if new_transaction:
                self.commit()

    def _unwrap_db_connection(self):
        """
        Obtém a conexão DBAPI real, independentemente de estar encapsulada
        por SQLAlchemy ou não.
        """
        connection = self._db
        visited = set()

        while True:
            candidate = None

            for attr in ("driver_connection", "connection", "dbapi_connection"):
                if hasattr(connection, attr):
                    attr_value = getattr(connection, attr)
                    if attr_value is not None and attr_value is not connection:
                        candidate = attr_value
                        break

            if candidate is None or id(candidate) in visited:
                return connection

            visited.add(id(candidate))
            connection = candidate

    @staticmethod
    def _context_rows_to_dict(context) -> List[dict]:
        rows = getattr(context, "rows", None)
        columns = getattr(context, "columns", None)

        if not rows or not columns:
            return []

        column_names = [column.get("name") for column in columns]
        return [
            {column_names[idx]: row[idx] for idx in range(len(column_names))}
            for row in rows
        ]

    @staticmethod
    def _cursor_rows_to_dict(cursor) -> List[dict]:
        description = getattr(cursor, "description", None)
        if not description:
            return []

        column_names = [col[0] for col in description]
        result_rows = cursor.fetchall()
        return [
            {column_names[idx]: row[idx] for idx in range(len(column_names))}
            for row in result_rows
        ]
