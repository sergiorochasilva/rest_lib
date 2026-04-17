from typing import List

from rest_lib.descriptor.dto_sql_join_field import DTOJoinFieldType


class JoinAux:
    def __init__(self) -> None:
        self.table: str = None
        self.type: DTOJoinFieldType = None
        self.fields: List[str] = None
        self.self_field: str = None
        self.other_field: str = None
        self.alias: str = None
