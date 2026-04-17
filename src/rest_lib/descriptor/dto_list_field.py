import typing

from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)
from rest_lib.exception import DTOListFieldConfigException
from rest_lib.util.fields_util import FieldsTree, build_fields_tree


# TODO Validar preenchimento da propriedade related_entity_field


class DTOListField:
    _ref_counter = 0

    description: str

    def __init__(
        self,
        dto_type: DTOBase,
        entity_type: EntityBase = None,
        related_entity_field: str = None,
        not_null: bool = False,
        min: int = None,
        max: int = None,
        validator: typing.Callable = None,
        dto_post_response_type: DTOBase = None,
        relation_key_field: str = None,
        service_name: str = None,
        description: str = "",
        use_integrity_check: bool = True,
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
        -----------
        Parameters:
        -----------

        - dto_type: Expected type for the related DTO (must be subclasse from DTOBase).

        - entity_type: Expected entity type for the related DTO (must be subclasse from EntityBase).

        - not_null: The field cannot be None (or an empty list).

        - min: Minimum number of itens in the list.

        - max: Maximum number of itens in the list.

        - validator: Function that receives the value (to be setted), and returns the same value (after any adjust).
            This function overrides the default behaviour and all default constraints.

        - related_entity_field: Fields, from related entity, used for relation in database.

        - insert_function_field: Nome da propriedade equivalente no InsertFunctionType. Se não informado, assume o nome do campo do DTO.

        - relation_key_field: Nome do campo, no DTO corrente, utilizado como chave de apontamento no relacionamento
            (isso é, campo para o qual a entidade, do lado N, aponta via FK).

        - insert_function_field: Nome da propriedade equivalente no InsertFunctionType quando o campo lista precisar apontar para um nome diferente (default: o nome do campo no DTO).

        - update_function_field: Nome da propriedade equivalente no UpdateFunctionType.

        - get_function_field: Nome do campo equivalente no Get/ListFunctionType (default: o próprio nome do campo no DTO).

        - delete_function_field: Nome do campo equivalente no DeleteFunctionType (default: o próprio nome do campo no DTO).

        - service_name: Nome do serviço customizado, caso se deseje que as operações sobre esse tipo de lista se façam
            de um modo customizado (e não usando o service_base do próprio RestLib).

        - description: Descrição deste campo na documentação.

        - use_integrity_check: Se o campo deve ser usado na geração de hash de registro para a api de verificação de integridade (ver IntegrityCheckRoute).

        - resume_fields: Lista de campos (usando a mesma sintaxe do parâmetro "fields" das chamadas GET)
            pertencentes ao DTO relacionado que devem ser incluídos automaticamente nas respostas.

        - convert_to_function: Função chamada para converter os objetos da lista antes de popular o InsertFunctionType. Recebe (lista_de_valores, dict_com_valores_do_dto) e deve retornar um dicionário com os campos/resultados que serão atribuídos no InsertFunctionType.
        """
        self.name = None
        self.description = description
        self.dto_type = dto_type
        self.entity_type = entity_type
        self.related_entity_field = related_entity_field
        self.insert_function_field = insert_function_field
        self.insert_function_type = insert_function_type
        self.update_function_field = update_function_field
        self.update_function_type = update_function_type
        self.not_null = not_null
        self.min = min
        self.max = max
        self.validator = validator
        self.dto_post_response_type = dto_post_response_type
        self.relation_key_field = relation_key_field
        self.service_name = service_name
        self.use_integrity_check = use_integrity_check
        self.resume_fields = list(resume_fields or [])
        self.resume_fields_tree: FieldsTree = build_fields_tree(self.resume_fields)
        self.convert_to_function = convert_to_function
        self.get_function_field = get_function_field
        self.delete_function_field = delete_function_field

        self.storage_name = f"_{self.__class__.__name__}#{self.__class__._ref_counter}"
        self.__class__._ref_counter += 1

        # Checking correct usage
        if self.dto_type is None:
            raise DTOListFieldConfigException("type parameter must be not None.")

        if service_name is None:
            if self.entity_type is None:
                raise DTOListFieldConfigException(
                    "entity_type parameter must be not None."
                )

        if (
            self.insert_function_type is not None
            and not issubclass(self.insert_function_type, InsertFunctionTypeBase)
        ):
            raise DTOListFieldConfigException(
                "insert_function_type deve herdar de InsertFunctionTypeBase."
            )

        if (
            self.update_function_type is not None
            and not issubclass(self.update_function_type, UpdateFunctionTypeBase)
        ):
            raise DTOListFieldConfigException(
                "update_function_type deve herdar de UpdateFunctionTypeBase."
            )

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.storage_name]

    def __set__(self, instance, value):
        try:
            if self.validator is None:
                value = self.validate(value)
            else:
                value = self.validator(value)
        except ValueError:
            if not (
                "escape_validator" in instance.__dict__
                and instance.__dict__["escape_validator"] is True
            ):
                raise

        # Preenchendo os campos de particionanmento, se necessário (normalmente: tenant e grupo_empresarial)
        self.set_partition_fields(instance, value)

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

    def set_partition_fields(self, instance, value):
        """
        Preenchendo os campos de particionanmento dos objetos da lista, se necessário (normalmente: tenant e grupo_empresarial).
        """

        if hasattr(instance.__class__, "partition_fields") and value is not None:
            for item in value:
                for partition_field in instance.__class__.partition_fields:
                    if (
                        hasattr(instance, partition_field)
                        and hasattr(item, partition_field)
                        # TODO Analisar se devo descomentar a comparação abaixo que deixa gravar com campos de partição
                        # diferentes entre classe mestre e detalhe (caso se especifique diferente no detalhe)
                        # Talvez falte aqui a comparação de tipo de relacionamento como composição (quando não é composição
                        # a diferença pode fazer sentido)
                        # and getattr(item, partition_field) is None
                        and getattr(instance, partition_field)
                        != getattr(item, partition_field)
                    ):
                        partition_value = getattr(instance, partition_field)
                        setattr(item, partition_field, partition_value)

    def validate(self, value):
        """
        Default validator (ckecking default constraints: not null, type, min and max).
        """

        # Checking not null constraint
        if (self.not_null) and (
            value is None or (isinstance(value, list) and len(value) <= 0)
        ):
            raise ValueError(
                f"O campo {self.storage_name} deve ser preechido. Valor recebido: {value}."
            )

        # Checking if received value is a list
        if value is not None and not isinstance(value, list):
            raise ValueError(
                f"O valor recebido para o campo {self.storage_name} deveria ser uma lista. Valor recebido: {value}."
            )

        # Checking type constraint
        # TODO Ver como suportar typing
        if (
            self.dto_type is not None
            and value is not None
            and len(value) > 0
            and not isinstance(value[0], self.dto_type)
        ):
            raise ValueError(
                f"Os items da lista {self.storage_name} deveriam se do tipo {self.dto_type.__name__}. Valor recebido: {value}."
            )

        # Checking min constraint
        if self.min is not None and (value is None or len(value) < self.min):
            raise ValueError(
                f"A lista {self.storage_name} deve ter mais do que {self.min} itens. Valor recebido: {value}."
            )

        # Checking max constraint
        if self.max is not None and value is not None and len(value) > self.max:
            raise ValueError(
                f"A lista {self.storage_name} deve ter menos do que {self.max} itens. Valor recebido: {value}."
            )

        return value
