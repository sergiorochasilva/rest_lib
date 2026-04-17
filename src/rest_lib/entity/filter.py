from typing import Any

from rest_lib.descriptor.filter_operator import FilterOperator


class Filter:
    """
    Representa uma condição de filtro para construção de SQL.

    Pode armazenar metadados de relacionamento para suportar filtros
    em entidades filhas via subquery ``exists``.
    """

    def __init__(
        self,
        operator: FilterOperator,
        value: Any,
        table_alias: str = None,
        relation_mode: str = None,
        relation_table: str = None,
        relation_parent_field: str = None,
        relation_child_field: str = None,
        relation_join_sql: str = None,
    ):
        """
        Inicializa um filtro com operador, valor e contexto relacional opcional.

        Args:
            operator (FilterOperator): Operador de comparação.
            value (Any): Valor do filtro.
            table_alias (str, optional): Alias SQL da tabela alvo.
            relation_mode (str, optional): Modo relacional (ex.: ``exists``).
            relation_table (str, optional): Tabela relacional usada no ``exists``.
            relation_parent_field (str, optional): Campo da tabela principal.
            relation_child_field (str, optional): Campo da tabela relacional.
            relation_join_sql (str, optional): SQL adicional de join no bloco relacional.

        Returns:
            None
        """
        self.operator = operator
        self.value = value
        self.table_alias = table_alias
        self.relation_mode = relation_mode
        self.relation_table = relation_table
        self.relation_parent_field = relation_parent_field
        self.relation_child_field = relation_child_field
        self.relation_join_sql = relation_join_sql

    def __repr__(self) -> str:
        return f"{self.value}"
