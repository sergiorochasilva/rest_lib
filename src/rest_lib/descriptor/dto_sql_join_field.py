import typing

from rest_lib.descriptor.dto_left_join_field import EntityRelationOwner
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.util.type_validator_util import TypeValidatorUtil


class DTOJoinFieldType:
    LEFT = "left"
    INNER = "inner"
    FULL = "full outer"


# TODO Adicionar suporte ao search
# TODO Implementar o filters comentado no construtor
# TODO Pensar em como ordenar os joins (quando tiver um left no meio, pode ser útil)
# TODO Pensar em como passar mais condições dentro do ON
# TODO Pensar em como usar um só entity (e não precisar de um com os campos que vem da outra entidade)
# TODO Verificar se ficou boa a abstração pelo DTO (porque o join ficou bem distante do natural em SQL)


class DTOSQLJoinField:
    _ref_counter = 0

    description: str
    partition_data: bool

    def __init__(
        self,
        dto_type: DTOBase,
        entity_type: EntityBase,
        related_dto_field: str,
        relation_field: str,
        entity_relation_owner: EntityRelationOwner = EntityRelationOwner.SELF,
        join_type: DTOJoinFieldType = DTOJoinFieldType.INNER,
        type: object = None,
        not_null: bool = False,
        resume: bool = False,
        convert_from_entity: typing.Callable = None,
        validator: typing.Callable = None,
        use_default_validator: bool = True,
        description: str = '',
        partition_data: bool = False,
    ):
        """
        -----------
        Parameters:
        -----------

        - dto_type: Expected type for the related DTO (must be subclasse from DTOBase).

        - entity_type: Expected entity type for the related DTO (must be subclasse from EntityBase).

        - related_dto_field: Nome do campo, no DTO relacionado, a ser copiado para esse campo.

        - relation_field: Nome do campo, usado na query, para correlacionar as entidades (correspondete
            ao campo usado no "on" de um "join").

        - entity_relation_owner: Indica qual entidade contém o campo que aponta o relacionamento (
            se for EntityRelationField.OTHER, implica que a entidade apontada pela classe de DTO
            passada no decorator, é que contem o campo; se for o EntityRelationField.SELF, indica
            que o próprio DTO que contém o campo).

        - join_type: Indica o tipo de Join a ser realizado na query (LEFT, INNER ou FULL).

        - type: Tipo esperado para a propriedade. Se for do tipo enum.Enum, o valor recebido, para atribuição à propriedade, será convertido para o enumerado.

        - not_null: O campo não poderá ser None, ou vazio, no caso de strings.

        - resume: O campo será usado como resumo, isto é, será sempre rotornado num HTTP GET que liste os dados (mesmo que não seja solicitado por meio da query string "fields").

        - convert_from_entity: Função para converter o valor contido na Entity, para o(s) valor(es) a serem gravados no objeto DTO (durante a conversão). É útil para casos onde não há equivalência um para um entre um campo do DTO e um da entidade
            (por exemplo, uma chave de cnpj que pode ser guardada em mais de um campo do BD). Outro caso de uso, é quando um campo tem formatação diferente entre o DTO e a entidade, carecendo de conversão customizada.
            A função recebida deve suportar os parâmetros (entity_value: Any, entity_fields: Dict[str, Any]), e retornar um Dict[str, Any], como uma coleção de chaves e valores a serem atribuídos no DTO.

        - validator: Função que recebe o valor (a ser atribuído), e retorna o mesmo valor após algum
            tipo de tratamento (como adição ou remoção, automática, de formatação).

        - use_default_validator: Flag indicando se o validator padrão deve ser aplicado à propriedade
            (esse validator padrão verifica o tipo de dados passado, e as demais verificações
            recebidas no filed, como, por exemplo, valor máximo, mínio, not_null, etc).

        - description: Descrição deste campo na documentação.

        - partition_data: Flag indicando se esta propriedade participa dos campos de particionamento da entidade, isto é, campos sempre usados nas queries de listagem gravação dos dados, inclusíve para recuperação de entidades relacionadas.
        """
        self.name = None
        self.description = description
        self.dto_type = dto_type
        self.entity_type = entity_type
        self.related_dto_field = related_dto_field
        self.relation_field = relation_field
        self.entity_relation_owner = entity_relation_owner
        self.join_type = join_type
        self.expected_type = type
        self.not_null = not_null
        self.resume = resume
        self.convert_from_entity = convert_from_entity
        self.validator = validator
        self.use_default_validator = use_default_validator
        self.partition_data = partition_data

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        self.__class__._ref_counter += 1

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.storage_name]

    def __set__(self, instance, value):
        try:
            # Checking not null constraint
            if self.not_null and (
                value is None or (isinstance(value, str) and len(value.strip()) <= 0)
            ):
                raise ValueError(
                    f"{self.storage_name} deve estar preenchido. Valor recebido: {value}."
                )

            if self.validator is None and value is not None:
                if self.use_default_validator:
                    value = TypeValidatorUtil.validate(self, value)
            else:
                if self.use_default_validator and value is not None:
                    value = TypeValidatorUtil.validate(self, value)

                if self.validator is not None:
                    value = self.validator(self, value)
        except ValueError as e:
            if not (
                "escape_validator" in instance.__dict__
                and instance.__dict__["escape_validator"] == True
            ):
                raise

        instance.__dict__[self.storage_name] = value


class SQLJoinQuery:
    related_dto: DTOBase
    related_entity: EntityBase
    fields: list[str]
    join_fields: list[DTOSQLJoinField]
    entity_relation_owner: EntityRelationOwner
    join_type: DTOJoinFieldType
    relation_field: str
    sql_alias: str

    def __init__(self) -> None:
        self.related_dto: DTOBase = None
        self.related_entity: EntityBase = None
        self.fields: list[str] = []
        self.related_fields: list[str] = []
        self.join_fields: list[DTOSQLJoinField] = []
        self.entity_relation_owner: EntityRelationOwner = None
        self.join_type: DTOJoinFieldType = None
        self.relation_field = None
        self.sql_alias = None
