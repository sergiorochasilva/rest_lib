import enum
import typing as ty

from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)

from .dto_field import DTOField

if ty.TYPE_CHECKING is True:
    from rest_lib.dto.dto_base import DTOBase
    from .dto_left_join_field import EntityRelationOwner

    pass

T = ty.TypeVar('T')


class OTORelationType(enum.IntEnum):
    """The enum for Relation Type for One to One relations."""

    COMPOSITION = 0
    AGGREGATION = 1
    pass


# pylint: disable=too-many-instance-attributes
class DTOOneToOneField:
    _ref_counter = 0

    expected_type: ty.Type['DTOBase']
    relation_type: OTORelationType
    field: DTOField
    entity_relation_owner: 'EntityRelationOwner'
    not_null: bool
    resume: bool
    partition_data: bool
    entity_field: str
    relation_field: str
    insert_function_field: str
    update_function_field: str
    validator: ty.Optional[ty.Callable[..., ty.Any]]
    description: str
    convert_to_function: ty.Optional[ty.Callable[..., ty.Any]]

    def __init__(
        self,
        entity_type: ty.Type[EntityBase],
        relation_type: OTORelationType,
        resume: bool = False,
        entity_field: ty.Optional[str] = None,
        entity_relation_owner: 'EntityRelationOwner' = 'self',  # type: ignore
        not_null: bool = False,
        partition_data: bool = False,
        validator: ty.Optional[ty.Callable[['DTOOneToOneField', T], T]] = None,
        description: str = '',
        insert_function_field: ty.Optional[str] = None,
        insert_function_type: ty.Optional[ty.Type[InsertFunctionTypeBase]] = None,
        update_function_field: ty.Optional[str] = None,
        update_function_type: ty.Optional[ty.Type[UpdateFunctionTypeBase]] = None,
        convert_to_function: ty.Optional[ty.Callable[..., ty.Any]] = None,
        get_function_field: ty.Optional[str] = None,
        delete_function_field: ty.Optional[str] = None,
        relation_field: ty.Optional[str] = None,
    ):
        """Descriptor used for One to One relations.
        ---------
        Glossary:
        ---------
        - Current DTO: Refers to the DTO that this field is a part of.
        - Related DTO: Refers to the DTO in the annotation of this field.


        -----
        NOTE:
        -----
        At the moment only `entity_relation_owner=EntityRelationOwner.SELF` is
            supported.

        -----------
        Parameters:
        -----------

        - entity_type: Entity type of the `Related DTO`
            (must be a subclasse from EntityBase).

        - relation_type: The type of relation of this field, one of:
            - OTORelationType.COMPOSITION:
                - During POST requests, it attempts to insert the data into the
                    `entity_type` table.
                - During PUT or PATCH requests, it attempts to update the
                    existing records in the `entity_type` table.
            - OTORelationType.AGGREGATION:
                - This type does not interact with the `entity_type` table.
                - It is relevant only in POST, PUT, or PATCH requests if the
                    `relation_field` is `None`. In this case, the value in the
                    `pk_field` of the `Related DTO` will be used in place of
                    the object.

        - relation_field: Field name in the `entity_type` to use in the `on` of
            the `join` query. Defaults to the `pk_field` of the `entity_type`.

        - resume: Indicates if on GET requests the non expanded value should be
            always returned.

        - entity_field: The name of the field in the Entity of the `Current DTO`.
            If `None` will use the name of the field in the `Current DTO`.

        - insert_function_field: Nome opcional do campo correspondente no InsertFunctionType (default: nome do campo no DTO).

        - update_function_field: Nome opcional do campo correspondente no UpdateFunctionType (default: herdado do campo de insert).

        - entity_relation_owner: Indicates which entity contain the
            `relation_field`, it must be one of:
                - EntityRelationField.SELF: The `relation_field` is part of the
                    `Current DTO`.
                - EntityRelationField.OTHER: The `relation_field` is part os the
                    `Related DTO`.

        - not_null: If the field can not be `None`. Only relevant in POST, PUT
            or PATCH requests.

        - partition_data: If the propertie is obligatory when listing(GET/LIST)
            including on relations.

        - validator: Function that receives the instance of this class and the
            value to be checked and returns it. For validation erros MUST throw
            ValueError. Errors are only honored on POST, PUT or PATCH requests.
            When `OTORelationType.AGGREGATION` the value passed will be the value
            in the `pk_field` of the `Related DTO`.

        - description: Description of this field that can be used in
            documentation.

        - convert_to_function: Função usada para converter o valor antes de popular o InsertFunctionType. Recebe (valor, dict_com_valores_do_dto) e deve retornar um dicionário com os campos/resultados a atribuir.

        - get_function_field: Nome do campo equivalente no Get/ListFunctionType (default: o próprio nome do campo no DTO).

        - delete_function_field: Nome do campo equivalente no DeleteFunctionType (default: o próprio nome do campo no DTO).
        """
        self.entity_type = entity_type
        self.relation_type = relation_type
        self.resume = resume
        self.entity_field = entity_field or ''
        self.insert_function_field = insert_function_field
        self.insert_function_type = insert_function_type
        self.update_function_field = update_function_field
        self.update_function_type = update_function_type
        self.entity_relation_owner = entity_relation_owner
        self.not_null = not_null
        self.partition_data = partition_data
        self.validator = validator
        self.description = description
        self.convert_to_function = convert_to_function
        self.get_function_field = get_function_field
        self.delete_function_field = delete_function_field
        self.relation_field = relation_field or ''

        self.name = None
        self.expected_type = ty.cast(ty.Type['DTOBase'], type)

        self.storage_name = (
            f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        )
        self.__class__._ref_counter += 1

        if (
            self.insert_function_type is not None
            and not issubclass(self.insert_function_type, InsertFunctionTypeBase)
        ):
            raise ValueError(
                "insert_function_type deve herdar de InsertFunctionTypeBase."
            )

        if (
            self.update_function_type is not None
            and not issubclass(self.update_function_type, UpdateFunctionTypeBase)
        ):
            raise ValueError(
                "update_function_type deve herdar de UpdateFunctionTypeBase."
            )

        # NOTE: To support EntityRelationOwner.OTHER you will have to modify
        #           `_retrieve_one_to_one_fields in ServiceBase`. do NOT forget
        #           to change the documentation.
        assert (
            self.entity_relation_owner == 'self'
        ), "At the moment only `EntityRelationOwner.SELF` is supported."

        assert issubclass(self.entity_type, EntityBase), (
            f"Argument `entity_type` of `DTOOneToOneField` HAS to be"
            f" a `EntityBase`. Is {repr(self.entity_type)}."
        )

        if self.relation_field == '':
            self.relation_field = self.entity_type.pk_field
            pass

        assert self.relation_field in self.entity_type.fields_map, (
            f"Argument `relation_field` of `DTOOneToOneField` HAS to be"
            f" a field of `{repr(self.entity_type)}`. Is {repr(self.relation_field)}."
        )

        pass

    def __get__(self, instance: ty.Optional['DTOBase'], owner: ty.Any):
        if instance is None:
            return self
        return instance.__dict__[self.storage_name]

    def __set__(
        self, instance: ty.Optional['DTOBase'], value: ty.Optional[ty.Any]
    ) -> None:
        escape_validator: bool = False
        if (
            'escape_validator' in instance.__dict__
            and instance.__dict__['escape_validator'] is True
        ):
            escape_validator = True
            pass

        try:
            if self.not_null is True and value is None:
                raise ValueError(f"{self.storage_name} deve ser preenchido.")

            if value is None:
                instance.__dict__[self.storage_name] = None
                return

            if self.relation_type == OTORelationType.AGGREGATION:
                if escape_validator is True:
                    if isinstance(value, dict):
                        value = self.expected_type(**value)
                        pass
                else:
                    if isinstance(value, self.expected_type):
                        value = getattr(value, self.relation_field, None)
                    elif isinstance(value, dict):
                        value_aux = value.get(self.relation_field, None)
                        if value_aux is None:
                            value_aux = value.get(self.expected_type.pk_field, None)
                        value = value_aux
                        pass
                    pass

                # NOTE: At this moment if the relation_field in the entity has
                #           a diferent name from the field on the DTO we disable
                #           validation, because at the moment there is no easy
                #           way to get a DTOField from the entity field name
                if isinstance(value, self.expected_type) and hasattr(value, self.relation_field):
                    relation_value = getattr(value, self.relation_field)
                    if self.field.use_default_validator:
                        # NOTE: This may throw
                        relation_value = self.field.validate(
                            self.field, relation_value, instance
                        )
                        pass

                    if self.field.validator is not None:
                        # NOTE: This may throw
                        relation_value = self.field.validator(
                            self.field, relation_value
                        )
                        pass

                    setattr(value, self.relation_field, relation_value)
                else:
                    if self.field.use_default_validator:
                        # NOTE: This may throw
                        value = self.field.validate(self.field, value, instance)
                        pass

                    if self.field.validator is not None:
                        # NOTE: This may throw
                        value = self.field.validator(self.field, value)
                        pass
                    pass
            else:  # self.relation_type == RelationType.COMPOSITION
                if isinstance(value, dict):
                    value = self.expected_type(**value)  # NOTE: This may throw
                    pass

                if not isinstance(value, self.expected_type):
                    raise ValueError(
                        f"{self.storage_name} deve ser do tipo: {self.expected_type}"
                    )
                if self.validator is not None:
                    value = self.validator(self, value)  # NOTE: This may throw
                    pass
                pass
        except ValueError:
            if escape_validator is False:
                raise
            pass

        instance.__dict__[self.storage_name] = value
        pass

    def get_insert_function_field_name(self) -> str:
        if self.insert_function_field is not None:
            return self.insert_function_field
        return self.name

    def get_update_function_field_name(self) -> str:
        if self.update_function_field is not None:
            return self.update_function_field
        return self.get_insert_function_field_name()

    def get_function_field_name(self, operation: str) -> str:
        if operation in ("get", "list"):
            if self.get_function_field is not None:
                return self.get_function_field
            return self.name
        if operation == "delete":
            if self.delete_function_field is not None:
                return self.delete_function_field
            return self.name
        if operation == "update":
            return self.get_update_function_field_name()
        return self.get_insert_function_field_name()

    def get_function_type(self, operation: str):
        if operation == "update" and self.update_function_type is not None:
            return self.update_function_type
        return self.insert_function_type
