import json
import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Mapping, Optional
from uuid import UUID

from rest_lib.util.json_util import convert_to_dumps

if TYPE_CHECKING:
    from rest_lib.descriptor.dto_sql_join_field import DTOSQLJoinField


class SQLUtils:
    """
    Utilitário para manipular instruções SQL.
    """

    _NAMED_PATTERN = re.compile(r"(?<!:):([a-zA-Z_][\w]*)")
    _PYFORMAT_PATTERN = re.compile(r"%\(([a-zA-Z_][\w]*)\)s")

    @classmethod
    def binding_args(
        cls, sql: str, params: Optional[Mapping[str, Any]] = None, **kwargs
    ) -> str:
        """
        Realiza o binding manual dos parâmetros para uma instrução SQL.
        Suporta as sintaxes :PARAM e %(PARAM)s.
        """
        if params and kwargs:
            values = {**params, **kwargs}
        elif params:
            values = dict(params)
        else:
            values = dict(kwargs)

        if not values:
            return sql

        converted = {key: cls._to_sql_literal(value) for key, value in values.items()}

        sql_with_pyformat = cls._PYFORMAT_PATTERN.sub(
            lambda match: cls._replace(match, converted), sql
        )

        return cls._NAMED_PATTERN.sub(
            lambda match: cls._replace(match, converted), sql_with_pyformat
        )

    @staticmethod
    def _replace(match: "re.Match[str]", converted: Mapping[str, str]) -> str:
        name = match.group(1)
        if name not in converted:
            raise KeyError(f"SQL placeholder '{name}' not found in parameters.")

        return converted[name]

    @classmethod
    def _to_sql_literal(cls, value: Any) -> str:
        if value is None:
            return "NULL"

        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"

        if isinstance(value, (int, float, Decimal)):
            return str(value)

        if isinstance(value, datetime):
            return cls._quote(value.isoformat(sep=" ", timespec="microseconds"))

        if isinstance(value, date):
            return cls._quote(value.isoformat())

        if isinstance(value, time):
            time_str = value.isoformat(timespec="microseconds")
            return cls._quote(time_str)

        if isinstance(value, (UUID, str)):
            return cls._quote(str(value))

        if isinstance(value, (bytes, bytearray)):
            hex_value = bytes(value).hex()
            return f"E'\\\\x{hex_value}'"

        if isinstance(value, set):
            value = list(value)

        if isinstance(value, dict):
            value = convert_to_dumps(value)
            return cls._quote(json.dumps(value, ensure_ascii=False))

        if isinstance(value, (list, tuple)):
            serialized = convert_to_dumps(list(value))
            return cls._quote(json.dumps(serialized, ensure_ascii=False))

        return cls._quote(str(value))

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"


def montar_chave_map_sql_join(field: "DTOSQLJoinField") -> str:
    return f"{field.dto_type}____{field.entity_type}____{field.entity_relation_owner}____{field.join_type}"
