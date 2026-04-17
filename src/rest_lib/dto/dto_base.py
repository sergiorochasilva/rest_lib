import abc
import copy
import enum

# import uuid

from typing import Any, Dict, List, Set, Union, Optional, Tuple, Literal

from rest_lib.entity.entity_base import EMPTY, EntityBase
from rest_lib.descriptor.dto_aggregator import DTOAggregator
from rest_lib.descriptor.dto_one_to_one_field import DTOOneToOneField
from rest_lib.descriptor.conjunto_type import ConjuntoType
from rest_lib.descriptor.dto_field import DTOField, DTOFieldFilter
from rest_lib.util.fields_util import (
    FieldsTree,
    clone_fields_tree,
    extract_child_tree,
    merge_fields_tree,
    normalize_fields_tree,
)
from rest_lib.util.enum_util import enum_to_primitive_value
from rest_lib.util.sql_utils import montar_chave_map_sql_join


class DTOBase(abc.ABC):
    resume_fields: Set[str] = set()
    partition_fields: Set[str] = set()
    fields_map: Dict[str, DTOField] = {}
    insert_function_field_lookup: Dict[str, Tuple[str, Any]] = {}
    update_function_field_lookup: Dict[str, Tuple[str, Any]] = {}
    get_function_field_lookup: Dict[str, Tuple[str, Any]] = {}
    list_function_field_lookup: Dict[str, Tuple[str, Any]] = {}
    delete_function_field_lookup: Dict[str, Tuple[str, Any]] = {}
    list_fields_map: dict = {}
    integrity_check_fields_map: dict = {}
    left_join_fields_map: dict = {}
    left_join_fields_map_to_query: dict = {}
    sql_join_fields_map: dict = {}
    sql_join_fields_map_to_query: dict = {}
    sql_read_only_fields: list = []
    sql_no_update_fields: Set[str] = set()
    object_fields_map: Dict[str, Any] = {}
    one_to_one_fields_map: Dict[str, DTOOneToOneField] = {}
    field_filters_map: Dict[str, DTOFieldFilter]
    aggregator_fields_map: Dict[str, DTOAggregator] = {}
    # TODO Refatorar para suportar PK composto
    pk_field: str
    fixed_filters: Dict[str, Any]
    conjunto_type: ConjuntoType
    conjunto_field: str
    escape_validator: bool
    uniques: Dict[str, Set[str]]
    candidate_keys: List[str]
    search_fields: Set[str]
    data_override_group: list[str]
    data_override_fields: list[str]
    return_hidden_fields: dict[str, any] = {}
    etag_fields: Set[str] = set()
    etag_type: Union[Literal["RAW"], Literal["DATE"], Literal["HASH"]] = "HASH"

    def __init__(
        self,
        entity: Union[EntityBase, dict] = None,
        escape_validator: bool = False,
        generate_default_pk_value: bool = True,
        validate_read_only: bool = False,
        kwargs_as_entity: bool = False,
        **kwargs,
    ) -> None:
        super().__init__()

        self.escape_validator = escape_validator
        self.generate_default_pk_value = generate_default_pk_value

        if entity is None and not kwargs_as_entity:
            self._provided_fields = set(kwargs.keys())
        else:
            self._provided_fields = set()

        # Transformando a entity em dict (se houver uma entity)
        if entity is not None:
            kwargs = (
                copy.deepcopy(entity)
                if type(entity) is dict
                else copy.deepcopy(entity.__dict__)
            )

        # NOTE: Creating this function as it will be used again when parsing
        #           DTOOneToOneField
        def set_field(dto_field: DTOField, field: str) -> None:
            if (
                validate_read_only
                and dto_field.read_only
                and kwargs.get(field, None) is not None
            ):
                raise ValueError(f"O campo {field} não pode ser preenchido.")

            # Tratando do valor default
            if (
                dto_field.default_value is not None
                and kwargs.get(field, None) is None
                and (not dto_field.pk or self.generate_default_pk_value)
            ):
                default_value = dto_field.default_value
                if callable(dto_field.default_value):
                    default_value = dto_field.default_value()
                kwargs[field] = default_value

            # Verificando se é preciso converter o nome do field para o nome
            #   correspondente no Entity. E, se será preciso aplicar alguma
            #   conversão customizada (para trazer o valor do entity para o DTO)
            entity_field = field
            if entity is not None or kwargs_as_entity:
                if dto_field.entity_field is not None:
                    entity_field = dto_field.entity_field

                # Verificando se o campo carece de conversão customizada
                if dto_field.convert_from_entity is not None:
                    fields_converted = dto_field.convert_from_entity(
                        kwargs[entity_field], kwargs
                    )
                    if field not in fields_converted:
                        setattr(self, field, None)

                    for converted_key in fields_converted:
                        setattr(self, converted_key, fields_converted[converted_key])

                    return

            # Atribuindo o valor à propriedade do DTO
            if entity_field in kwargs:
                setattr(self, field, kwargs[entity_field])
            else:
                setattr(self, field, None)
            return

        # Setando os campos registrados como fields simples
        for field in self.__class__.fields_map:
            # Recuperando a configuração do campo
            aux_dto_field = self.__class__.fields_map[field]

            set_field(aux_dto_field, field)

        # Setando os campos registrados como fields de join por meio da consulta SQL
        for field in self.__class__.sql_join_fields_map:
            # Recuperando a configuração do campo
            aux_dto_field = self.__class__.sql_join_fields_map[field]

            # Verificando a conversão do nome do field para o nome correspondente no Entity (no DTO Relacionado)
            # E, se será preciso aplicar alguma conversão customizada (para trazer o valor do entity para o DTO)
            entity_field = field
            if entity is not None or kwargs_as_entity:
                if (
                    aux_dto_field.related_dto_field
                    not in aux_dto_field.dto_type.fields_map
                ):
                    continue
                alias = self.__class__.sql_join_fields_map_to_query[
                    montar_chave_map_sql_join(aux_dto_field)
                ]
                entity_field = (
                    alias.sql_alias
                    + "_"
                    + aux_dto_field.dto_type.fields_map[
                        aux_dto_field.related_dto_field
                    ].get_entity_field_name()
                )

                # Verificando se o campo carece de conversão customizada
                if aux_dto_field.convert_from_entity is not None:
                    fields_converted = aux_dto_field.convert_from_entity(
                        kwargs[entity_field], kwargs
                    )
                    if field not in fields_converted:
                        setattr(self, field, None)

                    for converted_key in fields_converted:
                        setattr(self, converted_key, fields_converted[converted_key])

                    continue

            # Atribuindo o valor à propriedade do DTO
            if entity_field in kwargs:
                setattr(self, field, kwargs[entity_field])
            else:
                setattr(self, field, None)

        # Setando os campos registrados como fields left join
        for field in self.__class__.left_join_fields_map:
            # Recuperando a configuração do campo
            aux_dto_field = self.__class__.left_join_fields_map[field]

            # Atribuindo o valor à propriedade do DTO
            if field in kwargs:
                setattr(self, field, kwargs[field])
            else:
                setattr(self, field, None)

        # Setando os campos registrados como fields object
        for field in self.__class__.object_fields_map:
            # Recuperando a configuração do campo
            aux_dto_field = self.__class__.object_fields_map[field]

            # Atribuindo o valor à propriedade do DTO
            if field in kwargs and kwargs[field] is not None:
                if not isinstance(kwargs[field], dict):
                    raise ValueError(
                        f"O campo {field} deveria ser um dicionário com os campos da classe {aux_dto_field.dto_type}."
                    )
                else:
                    setattr(self, field, aux_dto_field.expected_type(**kwargs[field]))
            else:
                setattr(self, field, None)

        for oto_key, oto_field in self.__class__.one_to_one_fields_map.items():
            field = oto_field.entity_field

            # Entrada vinda da API: prefere o nome do DTO (ex.: "ativo_ti").
            # Entrada vinda de entity/kwargs_as_entity: aceita o campo fisico
            # correspondente (ex.: "id_ativo_ti").
            if oto_key in kwargs:
                oto_value = kwargs[oto_key]
            elif field in kwargs:
                oto_value = kwargs[field]
            else:
                oto_value = None

            if oto_value is None:
                setattr(self, oto_key, None)
                continue

            # Delega toda a validacao/conversao ao descriptor.
            setattr(self, oto_key, oto_value)
            pass

        for k, v in self.__class__.aggregator_fields_map.items():
            if k not in kwargs or kwargs[k] is None:
                if v.not_null is True:
                    raise ValueError(f"O campo {k} deve estar preenchido.")
                setattr(self, k, None)
                continue

            if isinstance(kwargs[k], v.expected_type):
                setattr(self, k, kwargs[k])
                continue

            if isinstance(kwargs[k], dict):
                setattr(self, k, v.expected_type(**kwargs[k]))
                continue

            raise ValueError(
                f"O campo {k} deveria ser um dicionário com"
                f" os campos da classe {v.expected_type}."
            )

        # Setando os campos registrados como fields de lista
        if entity is None:
            for field in self.__class__.list_fields_map:
                dto_list_field = self.__class__.list_fields_map[field]

                if field in kwargs:
                    if kwargs[field] is None:
                        continue
                    elif not isinstance(kwargs[field], list):
                        raise ValueError(
                            f"O campo {field} deveria ser uma lista do tipo {dto_list_field.dto_type}."
                        )

                    related_itens = []
                    for item in kwargs[field]:
                        # Preenchendo os campos de particionanmento, se necessário (normalmente: tenant e grupo_empresarial)
                        for partition_field in self.__class__.partition_fields:
                            if isinstance(item, dict):
                                if (
                                    (
                                        partition_field not in item
                                        or item[partition_field] is None
                                    )
                                    and partition_field
                                    in dto_list_field.dto_type.partition_fields
                                ):
                                    partition_value = getattr(self, partition_field)
                                    item[partition_field] = partition_value
                            elif isinstance(item, dto_list_field.dto_type):
                                if (
                                    not getattr(item, partition_field)
                                    and partition_field
                                    in dto_list_field.dto_type.partition_fields
                                ):
                                    partition_value = getattr(self, partition_field)
                                    setattr(item, partition_field, partition_value)
                            else:
                                raise ValueError(
                                    f"O campo {field} deveria ser uma lista do tipo {dto_list_field.dto_type}."
                                )

                        # Criando o DTO relacionado
                        if isinstance(item, dict):
                            item_dto = dto_list_field.dto_type(**item)
                        elif isinstance(item, dto_list_field.dto_type):
                            item_dto = item
                        else:
                            raise ValueError(
                                f"O campo {field} deveria ser uma lista do tipo {dto_list_field.dto_type}."
                            )

                        # Adicionando o DTO na lista do relacionamento
                        related_itens.append(item_dto)

                    setattr(self, field, related_itens)
                else:
                    setattr(self, field, None)

        # Tratando do ID automático
        # if generate_pk_uuid:
        #     if getattr(self, self.__class__.pk_field) is None:
        #         setattr(self, self.__class__.pk_field, uuid.uuid4())

        if self.escape_validator is False:
            self.validate_dto()
            pass
        pass

    def validate_dto(self) -> None:
        """
        Ponto de extensão para validações de nível DTO.

        Este método é chamado automaticamente ao final do __init__,
        depois que os campos e relacionamentos foram montados. Use-o
        para validar regras entre campos (dependências, limites,
        consistência etc.).

        Não use este método para atualizar valores de campos,
        pois quando self.escape_validator for True ele não será executado.

        Em caso de falha, lance ValueError ou uma outra exceção.
        """
        return None

    def convert_to_entity(
        self,
        entity_class: EntityBase,
        none_as_empty: bool = False,
        is_insert: bool = False,
    ) -> EntityBase:
        """
        Cria uma instância da entidade, e a popula com os dados do DTO
        corrente.

        É importante notar que as equivalências dos nomes dos campos
        são tratadas neste método.
        """

        entity: EntityBase = entity_class()

        for field, dto_field in self.__class__.fields_map.items():
            # Verificando se é preciso realizar uma tradução de nome do campo
            entity_field = field
            if dto_field.entity_field is not None:
                entity_field = dto_field.entity_field

            # Verificando se o campo existe na entity
            if not hasattr(entity, entity_field):
                continue

            # Recuperando o valor
            value = getattr(self, field)

            # Verificando se o campo é de auto incremento gerenciado pelo banco de dados, e,
            # se o valor é None pulando o campo para não entrar na query
            if (
                is_insert
                and dto_field.auto_increment is not None
                and dto_field.auto_increment.db_managed
                and value is None
            ):
                continue

            # Verificando se é necessária alguma conversão customizada
            custom_value_converted = DTOBase.custom_convert_value_to_entity(
                value,
                dto_field,
                entity_field,
                none_as_empty,
                self.__dict__,
            )
            if len(custom_value_converted) > 0:
                for key in custom_value_converted:
                    setattr(entity, key, custom_value_converted[key])
                    entity._sql_fields.append(key)
            else:
                # Convertendo o value para o correspondente nos fields
                value = DTOBase.convert_value_to_entity(
                    value,
                    dto_field,
                    none_as_empty,
                    entity_class,
                )

                # Setando na entidade
                setattr(entity, entity_field, value)
                entity._sql_fields.append(entity_field)

        for k, _ in self.__class__.aggregator_fields_map.items():
            dto = getattr(self, k)
            if dto is None:
                # NOTE: Skipping if the field was not given
                continue

            for agg_field, dto_field in dto.fields_map.items():
                entity_field = dto_field.entity_field or agg_field

                if hasattr(entity, entity_field) is False:
                    continue

                # pylint: disable-next=protected-access
                if entity_field in entity._sql_fields:
                    # NOTE: Skipping a field if it was already created
                    #           previously. This means that the field in
                    #           the base DTO is always.
                    continue

                value = getattr(dto, agg_field)
                custom_value_converted = DTOBase.custom_convert_value_to_entity(
                    value,
                    dto_field,
                    entity_field,
                    none_as_empty,
                    self.__dict__,
                )
                if len(custom_value_converted) > 0:
                    for k1, v1 in custom_value_converted.items():
                        setattr(entity, k1, v1)
                        # pylint: disable-next=protected-access
                        entity._sql_fields.append(k1)
                else:
                    val = DTOBase.convert_value_to_entity(
                        value,
                        dto_field,
                        none_as_empty,
                        entity_class,
                    )

                    setattr(entity, entity_field, val)
                    # pylint: disable-next=protected-access
                    entity._sql_fields.append(entity_field)

        return entity

    def custom_convert_value_to_entity(
        value: Any,
        dto_field: DTOField,
        entity_field: str,
        none_as_empty: bool,
        dto_values: Dict[str, any],
    ):
        # Verificando se é necessária uma conversão customizada
        retorno = {}
        if value is not None and dto_field.convert_to_entity is not None:
            fields_converted = dto_field.convert_to_entity(value, dto_values)
            if entity_field not in fields_converted:
                retorno[entity_field] = None if not none_as_empty else EMPTY

            for converted_key in fields_converted:
                value = fields_converted[converted_key]
                if value is None and none_as_empty:
                    value = EMPTY
                retorno[converted_key] = value

        return retorno

    def convert_value_to_entity(
        value: Any,
        dto_field: DTOField,
        none_as_empty: bool,
        entity_class: EntityBase,
    ) -> Any:
        # Enumerados
        if isinstance(dto_field.expected_type, enum.EnumMeta):
            try:
                # TODO Rever se não é para verificar se o valor já é do tipo enumerado, e só retornar seu value
                # (ou índice da tupla dentro do value, se houver uma tupla)
                # Porque parece que ele tenta sempre converter para o tipo esperado, mas isso pode já ter sido
                # feito no DTO
                return DTOBase._convert_enum_to_entity(value, dto_field, none_as_empty)
            except ValueError:
                # Retornando o pórpio valor, caso se deseje converter um enumerado que não seja válido
                # Isso é, aceitando enumerados inválidos (só para os filtros)
                return value.value if isinstance(value, enum.Enum) else str(value)

        # Bool to int
        entity_fields_map = getattr(entity_class, "fields_map", {})
        entity_field_name = dto_field.entity_field or dto_field.name
        if (
            isinstance(value, bool)
            and entity_field_name in entity_fields_map
            and entity_fields_map[entity_field_name].expected_type == int
        ):
            if value is None and none_as_empty:
                return EMPTY
            return 1 if value else 0

        # Convertendo None para EMPTY (se desejado)
        if value is None:
            if none_as_empty:
                return EMPTY
            else:
                return value

        return value

    def _convert_enum_to_entity(value: Any, dto_field: DTOField, none_as_empty: bool):
        # Ignorando valores nulos
        if value is None:
            if none_as_empty:
                return EMPTY
            else:
                return None

        # Construindo uma lista com os itens do enumerado esperado
        lista_enum = list(dto_field.expected_type)

        # Se o enum estiver vazio
        if len(lista_enum) <= 0:
            return None

        # Verificando o tipo dos valores do enum
        if isinstance(lista_enum[0].value, tuple):
            # Recuperando o item correspondente do enumerado
            enumerado = value
            parou = False
            if not isinstance(value, dto_field.expected_type):
                for item in dto_field.expected_type:
                    lista_valores = list(item.value)
                    for valor in lista_valores:
                        if valor == value:
                            enumerado = item
                            parou = True
                            break

                        # Se o valor for string, testa inclusive em caixa alta e baixa
                        if isinstance(value, str):
                            if valor == value.lower() or valor == value.upper():
                                enumerado = item
                                parou = True
                                break

                    if parou:
                        break

            # Convertendo do enumerado para o valor desejado na entidade
            return enum_to_primitive_value(enumerado)
        else:
            # Tentando pelo valor do próprio enum (e testando os casos, se for str)
            if isinstance(value, str):
                try:
                    return dto_field.expected_type(value)
                except ValueError:
                    try:
                        return dto_field.expected_type(value.lower())
                    except ValueError:
                        return dto_field.expected_type(value.upper())
            else:
                return dto_field.expected_type(value)

    @classmethod
    def build_default_fields_tree(cls) -> FieldsTree:
        """
        Constrói a estrutura de fields para o DTO, com base nos campos
        configurados como resumo.

        A estrutura de fields é uma árvore, onde cada chave é o nome do campo
        e o valor é um conjunto de campos que são resumos.

        :return: Uma estrutura de fields em formato de árvore.
        :rtype: FieldsTree
        """
        tree: FieldsTree = {"root": set(cls.resume_fields)}

        for field_name, descriptor in cls.list_fields_map.items():
            if len(descriptor.resume_fields_tree.get("root", set())) <= 0:
                continue

            tree["root"].add(field_name)
            tree[field_name] = clone_fields_tree(descriptor.resume_fields_tree)

        for field_name, descriptor in cls.object_fields_map.items():
            if descriptor.resume or len(descriptor.resume_fields) > 0:
                tree["root"].add(field_name)

                if len(descriptor.resume_fields_tree.get("root", set())) > 0:
                    tree[field_name] = clone_fields_tree(descriptor.resume_fields_tree)

        for field_name, descriptor in cls.aggregator_fields_map.items():
            if field_name in tree["root"]:
                tree["root"] |= descriptor.expected_type.resume_fields

        for field_name, descriptor in cls.one_to_one_fields_map.items():
            if descriptor.field.resume:
                tree["root"].add(field_name)

        return tree

    def convert_to_dict(
        self,
        fields: Optional[FieldsTree] = None,
        expands: Optional[Dict[str, Set[str]]] = None,
        just_resume: bool = False,
    ):
        """
        Converte DTO para dict
        """

        # Resolving fields to use
        if just_resume:
            fields_tree = self.__class__.build_default_fields_tree()
        else:
            if fields is None:
                fields_tree = self.__class__.build_default_fields_tree()
            else:
                fields_tree = normalize_fields_tree(fields)
                merge_fields_tree(
                    fields_tree,
                    self.__class__.build_default_fields_tree(),
                )

        if expands is None:
            expands = {"root": set()}

        # Making result maps
        result = {}

        # Converting simple fields
        for field in self.fields_map:
            if field not in fields_tree["root"]:
                continue

            result[field] = getattr(self, field)

        # Converting sql join fields
        for field in self.sql_join_fields_map:
            if field not in fields_tree["root"]:
                continue

            result[field] = getattr(self, field)

        # Converting left join fields
        for field in self.left_join_fields_map:
            if field not in fields_tree["root"]:
                continue

            result[field] = getattr(self, field)

        for field in self.object_fields_map:
            if field not in fields_tree["root"]:
                continue

            result[field] = (
                getattr(self, field).convert_to_dict(
                    extract_child_tree(fields_tree, field)
                )
                if getattr(self, field) is not None
                else None
            )

        for field, oto_field in self.one_to_one_fields_map.items():
            if field not in fields_tree["root"] or field not in expands["root"]:
                continue

            if getattr(self, field) is None:
                result[field] = None
            else:
                if isinstance(getattr(self, field), oto_field.expected_type):
                    result[field] = getattr(self, field).convert_to_dict(
                        fields_tree[field] if field in fields_tree else None,
                        expands[field] if field in expands else None,
                    )
                    pass
                pass
            pass

        for k in self.aggregator_fields_map:
            if k not in fields_tree["root"]:
                continue

            value = getattr(self, k, None)
            if value is None:
                result[k] = None
                continue
            if hasattr(value, "convert_to_dict"):
                result[k] = value.convert_to_dict(
                    extract_child_tree(fields_tree, k),
                    extract_child_tree(expands, k),
                )
            else:
                result[k] = value

        # Converting list fields
        for field in self.list_fields_map:
            if field not in fields_tree["root"]:
                continue

            # Criando o mapa de fields para a entidade aninhada
            internal_fields = extract_child_tree(fields_tree, field)
            internal_expands = extract_child_tree(expands, field)

            # Recuperando o valor do atributo sem disparar descriptor em DTO incompleto
            value = self.__dict__.get(field, None)
            if value is None:
                result[field] = None
                continue

            # Convetendo a lista de DTOs aninhados
            result[field] = [
                (
                    item.convert_to_dict(
                        clone_fields_tree(internal_fields),
                        clone_fields_tree(internal_expands),
                        just_resume,
                    )
                    if item is not None and hasattr(item, "convert_to_dict")
                    else item
                )
                for item in value
            ]

        return result

    def get_entity_field_name(self, dto_field_name: str) -> str | None:
        """
        Retorna o nome correspondente do field no entity
        (o qual é o nome do field no DTO por padrão, ou o nome que for
        passado no parâmetro "entity_field" no construtor).

        Retorna None, se o "dto_field_name" não for achado como um dos
        fields registrados.
        """

        if dto_field_name not in self.fields_map:
            return None

        return self.fields_map[dto_field_name].get_entity_field_name()

    @classmethod
    def _filter_by_fields_tree(cls, value, fields_tree):
        if not isinstance(value, dict):
            return value

        root_fields = fields_tree.get("root", set())
        result = {}
        for field in root_fields:
            if field not in value:
                continue
            field_value = value[field]
            subtree = fields_tree.get(field)
            if subtree and isinstance(field_value, dict):
                result[field] = cls._filter_by_fields_tree(field_value, subtree)
            elif subtree and isinstance(field_value, list):
                result[field] = [
                    (
                        cls._filter_by_fields_tree(item, subtree)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in field_value
                ]
            else:
                result[field] = field_value
        return result

    @classmethod
    def get_params_normalizados(
        cls, body, query_args=None, path_args=None
    ) -> list | dict:
        """
        Normaliza o corpo da requisição, de acordo com as propriedades do DTO.
        """

        fields_tree = cls.build_default_fields_tree()
        if isinstance(body, list):
            normalized_body = [
                (
                    cls._filter_by_fields_tree(item, fields_tree)
                    if isinstance(item, dict)
                    else item
                )
                for item in body
            ]
        elif isinstance(body, dict):
            normalized_body = cls._filter_by_fields_tree(body, fields_tree)
        else:
            normalized_body = {}

        return normalized_body
