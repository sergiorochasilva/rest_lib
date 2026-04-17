import typing

from rest_lib.descriptor.dto_left_join_field import EntityRelationOwner
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)
from rest_lib.util.fields_util import FieldsTree, build_fields_tree


class DTOObjectField:
    _ref_counter = 0

    description: str

    def __init__(
        self,
        entity_type: EntityBase = None,
        relation_field: str = None,
        entity_relation_owner: EntityRelationOwner = EntityRelationOwner.SELF,
        not_null: bool = False,
        resume: bool = False,
        validator: typing.Callable = None,
        description: str = "",
        resume_fields: typing.Iterable[str] = None,
        insert_function_field: str = None,
        insert_function_type: typing.Optional[type[InsertFunctionTypeBase]] = None,
        update_function_field: str = None,
        update_function_type: typing.Optional[type[UpdateFunctionTypeBase]] = None,
        convert_to_function: typing.Callable = None,
        get_function_field: str = None,
        delete_function_field: str = None,
    ):
        """
        DEPRECATED! Use DTOOneToOneField instead!

        Ex:
        @DTO()
        class ADTO(DTOBase):
            id: ...
            b: BDTO = DTOObjectField(entity_type=BEntity, relation_field='id')

        Becomes:
        @DTO()
        class ADTO(DTOBase):
            id: ...
            b: BDTO = DTOOneToOneField(entity_type=BEntity,
                                       relation_type=OTORelationType.COMPOSITION,
                                       relation_field='id')

        -----------
        Parameters:
        -----------

        - entity_type: Expected entity type for the related DTO (must be subclasse from EntityBase).

        - relation_field: Nome do campo, usado na query, para correlacionar as entidades (correspondete
            ao campo usado no "on" de um "join").

        - entity_relation_owner: Indica qual entidade contém o campo que aponta o relacionamento (
            se for EntityRelationField.OTHER, implica que a entidade apontada pela classe de DTO
            passada no decorator, é que contem o campo; se for o EntityRelationField.SELF, indica
            que o próprio DTO que contém o campo).

        - type: Tipo esperado para a propriedade. Se for do tipo enum.Enum, o valor recebido, para atribuição à propriedade, será convertido para o enumerado.

        - not_null: O campo não poderá ser None, ou vazio, no caso de strings.

        - resume: O campo será usado como resumo, isto é, será sempre rotornado num HTTP GET que liste os dados (mesmo que não seja solicitado por meio da query string "fields").

        - resume_fields: Campos do DTO relacionado que devem ser incluídos automaticamente nas respostas,
            seguindo a sintaxe do parâmetro "fields" (suporta aninhamentos com ".").

        - validator: Função que recebe o valor (a ser atribuído), e retorna o mesmo valor após algum
            tipo de tratamento (como adição ou remoção, automática, de formatação).

        - description: Descrição deste campo na documentação.

        - insert_function_field: Nome do campo equivalente no InsertFunctionType (default: o nome do campo no DTO).

        - update_function_field: Nome do campo equivalente no UpdateFunctionType (default: herdado do insert_function_field).

        - convert_to_function: Função para converter o valor antes de preencher o InsertFunctionType. Recebe (valor, dict_com_valores_do_dto) e deve retornar um dicionário com os campos/resultados a serem atribuídos.

        - get_function_field: Nome do campo equivalente no Get/ListFunctionType (default: o próprio nome do campo no DTO).

        - delete_function_field: Nome do campo equivalente no DeleteFunctionType (default: o próprio nome do campo no DTO).
        """
        self.name = None
        self.description = description
        self.entity_type = entity_type
        self.relation_field = relation_field
        self.entity_relation_owner = entity_relation_owner
        self.expected_type = type
        self.not_null = not_null
        self.resume = resume
        self.validator = validator
        self.resume_fields = list(resume_fields or [])
        self.resume_fields_tree: FieldsTree = build_fields_tree(self.resume_fields)
        self.insert_function_field = insert_function_field
        self.insert_function_type = insert_function_type
        self.update_function_field = update_function_field
        self.update_function_type = update_function_type
        self.convert_to_function = convert_to_function
        self.get_function_field = get_function_field
        self.delete_function_field = delete_function_field

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
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

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.storage_name]

    def __set__(self, instance, value):
        try:
            # Checking not null constraint
            if self.not_null and value is None:
                raise ValueError(
                    f"{self.storage_name} deve estar preenchido. Valor recebido: {value}."
                )

            if value is not None:
                if not isinstance(value, self.expected_type):
                    raise ValueError(
                        f"O Objeto não é do tipo informado. Valor recebido: {value}."
                    )

            if self.validator is not None:
                value = self.validator(self, value)
        except ValueError:
            if not (
                "escape_validator" in instance.__dict__
                and instance.__dict__["escape_validator"] == True
            ):
                raise

        instance.__dict__[self.storage_name] = value

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
