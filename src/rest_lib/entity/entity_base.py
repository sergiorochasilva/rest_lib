import abc

from typing import Dict, List

from rest_lib.descriptor.entity_field import EntityField


class EMPTY:
    pass


class EntityBase(abc.ABC):
    fields_map: Dict[str, EntityField] = {}
    table_name: str = ""
    pk_field: str = ""
    default_order_fields: List[str] = []

    def __init__(self) -> None:
        super().__init__()
        self._sql_fields: list[str] = []
        if "fields_map" in self.__class__.__dict__:
            for field in self.__class__.fields_map:
                if field not in self.__dict__:
                    setattr(self, field, None)

    def initialize_fields(self):
        for annotation in self.__annotations__:
            self.__setattr__(annotation, None)

    def get_table_name(self) -> str:
        if hasattr(self.__class__, "table_name"):
            return self.__class__.table_name
        else:
            raise NotImplementedError(
                f"Método get_table_name não implementado na classe: {self.__class__}"
            )

    def get_default_order_fields(self) -> List[str]:
        if hasattr(self.__class__, "default_order_fields"):
            return self.__class__.default_order_fields
        else:
            raise NotImplementedError(
                f"Método get_default_order_fields não implementado na classe: {self.__class__}"
            )

    def get_pk_field(self) -> str:
        if hasattr(self.__class__, "pk_field"):
            return self.__class__.pk_field
        else:
            raise NotImplementedError(
                f"Método get_pk_field não implementado na classe: {self.__class__}"
            )

    def get_fields_map(self) -> str:
        if hasattr(self.__class__, "fields_map"):
            return self.__class__.fields_map
        else:
            raise NotImplementedError(
                f"Método get_fields_map não implementado na classe: {self.__class__}"
            )

    def get_insert_returning_fields(self) -> List[str]:
        return []

    def get_update_returning_fields(self) -> List[str]:
        return []

    def get_const_fields(self) -> List[str]:
        return ["criado_em", "criado_por"]
