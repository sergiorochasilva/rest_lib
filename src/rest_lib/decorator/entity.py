import functools

from dataclasses import dataclass
from typing import Any, List, Optional, Set, Type

from rest_lib.descriptor.entity_field import EntityField
from rest_lib.entity.entity_base import EntityBase


@dataclass
class PartialEntityConfig:
    parent_entity: Type[EntityBase]
    extension_table_name: str
    parent_fields: Set[str]
    extension_fields: Set[str]


class Entity:
    def __init__(
        self,
        table_name: Optional[str] = None,
        pk_field: Optional[str] = None,
        default_order_fields: Optional[List[str]] = None,
        partial_of: Optional[Type[EntityBase]] = None,
        partial_table_name: Optional[str] = None,
    ) -> None:
        super().__init__()

        self.partial_of = partial_of

        parent_table_name = None
        parent_pk_field = None
        parent_default_order_fields = None
        if partial_of is not None:
            if not isinstance(partial_of, type) or not issubclass(
                partial_of, EntityBase
            ):
                raise ValueError(
                    "Configuração partial_of inválida: a classe informada deve ser subclasse de EntityBase."
                )

            parent_table_name = getattr(partial_of, "table_name", None)
            parent_pk_field = getattr(partial_of, "pk_field", None)
            parent_default_order_fields = list(
                getattr(partial_of, "default_order_fields", []) or []
            )

        extension_table_name = partial_table_name
        if partial_of is not None:
            if extension_table_name is None:
                extension_table_name = table_name

            if extension_table_name is None:
                raise ValueError(
                    "Entidades parciais devem informar o nome da tabela de extensão por meio de 'partial_table_name' ou 'table_name'."
                )

            if table_name is None:
                table_name = parent_table_name
            else:
                table_name = parent_table_name

            if pk_field is None:
                pk_field = parent_pk_field

            if default_order_fields is None:
                default_order_fields = parent_default_order_fields
        else:
            if table_name is None or pk_field is None or default_order_fields is None:
                raise ValueError(
                    "Parâmetros 'table_name', 'pk_field' e 'default_order_fields' são obrigatórios para entidades sem partial_of."
                )

        if default_order_fields is None:
            default_order_fields = []
        else:
            default_order_fields = list(default_order_fields)

        if pk_field is not None and pk_field not in default_order_fields:
            default_order_fields.append(pk_field)

        self.table_name = table_name
        self.pk_field = pk_field
        self.default_order_fields = default_order_fields
        self.partial_table_name = extension_table_name
        self.parent_default_order_fields = parent_default_order_fields

    def __call__(self, cls: object):
        """
        Tratando dos tipos de dados dos atributos, e criando os getters necessários.
        """

        # Mantém metadados da classe original
        functools.update_wrapper(self, cls)

        # Extendendo as propriedades por meio das extensões parciais
        parent_fields: Set[str] = set()
        if self.partial_of is not None:
            parent_fields = set(getattr(self.partial_of, "fields_map", {}).keys())
            parent_annotations = dict(
                getattr(self.partial_of, "__annotations__", {}) or {}
            )
            current_annotations = dict(getattr(cls, "__annotations__", {}) or {})
            merged_annotations = parent_annotations
            merged_annotations.update(current_annotations)
            cls.__annotations__ = merged_annotations

            for key in parent_annotations:
                if key not in cls.__dict__:
                    setattr(cls, key, getattr(self.partial_of, key, None))

            setattr(cls, "partial_entity_parent", self.partial_of)
            setattr(cls, "partial_extension_table", self.partial_table_name)
        else:
            setattr(cls, "partial_entity_parent", None)
            setattr(cls, "partial_extension_table", None)

        # Guardando o nome da tabela na classe
        self._check_class_attribute(cls, "table_name", self.table_name)

        # Guardando o nome do campo PK na classe
        self._check_class_attribute(cls, "pk_field", self.pk_field)

        # Guardando a lista default de ordenação, na classe
        self._check_class_attribute(
            cls, "default_order_fields", self.default_order_fields
        )

        # Creating fields_map in cls, if needed
        self._check_class_attribute(cls, "fields_map", {})

        # Iterando pelos atributos de classe
        for key, attr in cls.__dict__.items():
            atributo = None

            # Copiando o tipo a partir da anotação de tipo (se existir)
            if isinstance(attr, EntityField):
                atributo = attr
            elif key in cls.__annotations__:
                atributo = attr
                if not isinstance(attr, EntityField):
                    atributo = EntityField()

            if atributo:
                # Setting a better name to storage_name
                atributo.storage_name = f"{key}"
                atributo.name = f"{key}"

                # Guardando o type esperado
                if key in cls.__annotations__:
                    atributo.expected_type = cls.__annotations__[key]

                # Guardando o atributo no fields_map
                getattr(cls, "fields_map")[key] = atributo

        # Gravando as configurações d eextensão parcial
        if self.partial_of is not None:
            extension_fields = {
                key
                for key in getattr(cls, "fields_map").keys()
                if key not in parent_fields
            }
            setattr(
                cls,
                "partial_entity_config",
                PartialEntityConfig(
                    parent_entity=self.partial_of,
                    extension_table_name=self.partial_table_name,
                    parent_fields=parent_fields,
                    extension_fields=extension_fields,
                ),
            )
        else:
            setattr(cls, "partial_entity_config", None)

        return cls

    def _check_class_attribute(self, cls: object, attr_name: str, default_value: Any):
        """
        Add attribute "attr_name" in class "cls", if not exists.
        """

        if attr_name not in cls.__dict__:
            setattr(cls, attr_name, default_value)
