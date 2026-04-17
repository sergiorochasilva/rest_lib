import typing

from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import DTOListFieldConfigException

from rest_lib.util.type_validator_util import TypeValidatorUtil


class EntityRelationOwner:
    SELF = "self"
    OTHER = "other"


class DTOLeftJoinField:
    _ref_counter = 0

    description: str

    def __init__(
        self,
        resume: bool,
        dto_type: DTOBase,
        entity_type: EntityBase,
        related_dto_field: str,
        relation_field: str,
        entity_relation_owner: EntityRelationOwner = EntityRelationOwner.SELF,
        type: object = None,
        validator: typing.Callable = None,
        use_default_validator: bool = True,
        description: str = '',
    ):
        """
        -----------
        Parameters:
        -----------
        resume: O campo será usado como resumo, isto é, será sempre rotornado num HTTP GET que liste
            os dados (mesmo que não seja solicitado por meio da query string "fields").
        dto_type: Expected type for the related DTO (must be subclasse from DTOBase).
        entity_type: Expected entity type for the related DTO (must be subclasse from EntityBase).
        related_dto_field: Nome do campo, no DTO relacionado, a ser copiado para esse campo.
        relation_field: Nome do campo, usado na query, para correlacionar as entidades (correspondete
            ao campo usado no "on" de um "join").
        entity_relation_owner: Indica qual entidade contém o campo que aponta o relacionamento (
            se for EntityRelationField.OTHER, implica que a entidade apontada pela classe de DTO
            passada no decorator, é que contem o campo; se for o EntityRelationField.SELF, indica
            que o próprio DTO que contém o campo).
        type: Tipo esperado para a propriedade. Se for do tipo enum.Enum, o valor recebido, para
            atribuição à propriedade, será convertido para o enumerado.
        validator: Função que recebe o valor (a ser atribuído), e retorna o mesmo valor após algum
            tipo de tratamento (como adição ou remoção, automática, de formatação).
        use_default_validator: Flag indicando se o validator padrão deve ser aplicado à propriedade
            (esse validator padrão verifica o tipo de dados passado, e as demais verificações
            recebidas no filed, como, por exemplo, valor máximo, mínio, not_null, etc).
        description: Descrição deste campo na documentação.
        """
        self.name = None
        self.description = description
        self.resume = resume
        self.expected_type = type
        self.dto_type = dto_type
        self.entity_type = entity_type
        self.related_dto_field = related_dto_field
        self.relation_field = relation_field
        self.entity_relation_owner = entity_relation_owner
        self.validator = validator
        self.use_default_validator = use_default_validator

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        self.__class__._ref_counter += 1

        # Checking correct usage
        if self.dto_type is None:
            raise DTOListFieldConfigException("type parameter must be not None.")

        if self.entity_type is None:
            raise DTOListFieldConfigException("entity_type parameter must be not None.")

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.storage_name]

    def __set__(self, instance, value):
        try:
            if self.validator is None:
                if self.use_default_validator and value is not None:
                    value = TypeValidatorUtil.validate(self, value)
            else:
                if self.use_default_validator and value is not None:
                    value = TypeValidatorUtil.validate(self, value)
                value = self.validator(self, value)
        except ValueError as e:
            if not (
                "escape_validator" in instance.__dict__
                and instance.__dict__["escape_validator"] == True
            ):
                raise

        instance.__dict__[self.storage_name] = value


class LeftJoinQuery:
    related_dto: DTOBase
    related_entity: EntityBase
    fields: list[str]
    left_join_fields: list[DTOLeftJoinField]
    entity_relation_owner: EntityRelationOwner

    def __init__(self) -> None:
        self.related_dto: DTOBase = None
        self.related_entity: EntityBase = None
        self.fields: list[str] = []
        self.left_join_fields: list[DTOLeftJoinField] = []
        self.entity_relation_owner: EntityRelationOwner = None
