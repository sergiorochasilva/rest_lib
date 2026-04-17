import copy
import uuid
import typing as ty

from typing import Any, Dict, List, Set, Tuple

from rest_lib.descriptor.dto_field import DTOFieldFilter
from rest_lib.descriptor.dto_left_join_field import EntityRelationOwner
from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.filter import Filter
from rest_lib.exception import NotFoundException
from rest_lib.util.fields_util import FieldsTree
from rest_lib.util.type_validator_util import TypeValidatorUtil
from rest_lib.validator.validate_data import validate_uuid


class ServiceBaseUtil:
    """
    Utilitários compartilhados do ServiceBase para conversões e filtros.

    Centraliza helpers de normalização de campos, resolução de chaves e
    transformação de filtros de DTO em filtros de Entity/SQL.
    """

    @staticmethod
    def _build_one_to_one_filter_alias(field_name: str) -> str:
        """
        Gera alias SQL estável para filtros em relacionamentos 1x1.

        Args:
            field_name (str): Nome do campo de relacionamento no DTO.

        Returns:
            str: Alias sanitizado no formato ``oto_<nome>``.
        """
        safe_name = "".join(
            character if character.isalnum() or character == "_" else "_"
            for character in str(field_name)
        )
        return f"oto_{safe_name}"

    @staticmethod
    def _build_list_filter_alias(field_name: str) -> str:
        """
        Gera alias SQL estável para filtros em relacionamentos 1xN.

        Args:
            field_name (str): Nome do campo de relacionamento no DTO.

        Returns:
            str: Alias sanitizado no formato ``lst_<nome>``.
        """
        safe_name = "".join(
            character if character.isalnum() or character == "_" else "_"
            for character in str(field_name)
        )
        return f"lst_{safe_name}"

    @staticmethod
    def _resolve_filter_suffix(
        raw_filter_name: str,
    ) -> Tuple[str, FilterOperator | None, str | None]:
        """
        Resolve sufixos de operação no nome do filtro.

        Exemplos:
            ``campo_maior`` -> (``campo``, ``GREATER_THAN``, ``raw``)
            ``campo_contem`` -> (``campo``, ``ILIKE``, ``contains``)
            ``campo_vazio`` -> (``campo``, ``NULL``, ``none``)

        Args:
            raw_filter_name (str): Nome do filtro recebido via query string.

        Returns:
            Tuple[str, FilterOperator | None, str | None]: Nome base do campo,
            operador inferido e modo de tratamento do valor.
        """
        if not isinstance(raw_filter_name, str):
            return raw_filter_name, None, None

        suffixes = [
            ("_maior_igual", FilterOperator.GREATER_OR_EQUAL_THAN, "raw"),
            ("_menor_igual", FilterOperator.LESS_OR_EQUAL_THAN, "raw"),
            ("_nao_vazio", FilterOperator.NOT_NULL, "none"),
            ("_comeca_com", FilterOperator.ILIKE, "starts_with"),
            ("_inicia_com", FilterOperator.ILIKE, "starts_with"),
            ("_termina_com", FilterOperator.ILIKE, "ends_with"),
            ("_nao_contem", FilterOperator.NOT_ILIKE, "contains"),
            ("_diferente", FilterOperator.DIFFERENT, "raw"),
            ("_differente", FilterOperator.DIFFERENT, "raw"),
            ("_contem", FilterOperator.ILIKE, "contains"),
            ("_maior", FilterOperator.GREATER_THAN, "raw"),
            ("_menor", FilterOperator.LESS_THAN, "raw"),
            ("_igual", FilterOperator.EQUALS, "raw"),
            ("_apos", FilterOperator.GREATER_THAN, "raw"),
            ("_antes", FilterOperator.LESS_THAN, "raw"),
            ("_vazio", FilterOperator.NULL, "none"),
            ("_like", FilterOperator.LIKE, "raw"),
            ("_ilike", FilterOperator.ILIKE, "raw"),
        ]

        for suffix, operator, value_mode in suffixes:
            if raw_filter_name.endswith(suffix):
                field_name = raw_filter_name[: -len(suffix)]
                if field_name != "":
                    return field_name, operator, value_mode

        return raw_filter_name, None, None

    @staticmethod
    def _apply_filter_value_mode(value: Any, value_mode: str | None) -> Any:
        """
        Ajusta o valor recebido conforme o modo da operação derivada por sufixo.

        Args:
            value (Any): Valor cru informado no filtro.
            value_mode (str | None): Modo de transformação (contains,
                starts_with, ends_with ou None).

        Returns:
            Any: Valor transformado para uso na cláusula SQL.
        """
        if value_mode is None or value is None:
            return value

        if not isinstance(value, str):
            return value

        if value_mode == "contains":
            return f"%{value}%"
        if value_mode == "starts_with":
            return f"{value}%"
        if value_mode == "ends_with":
            return f"%{value}"

        return value

    def _resolve_field_key(
        self,
        id_value: Any,
        partition_fields: Dict[str, Any],
    ) -> Tuple[str, Any]:
        """
        Verificando se o tipo de campo recebido bate com algum dos tipos dos campos chave,
        começando pela chave primária.

        Retorna uma tupla: (nome_campo_chave_na_entity, valor_chave_tratado_convertido_para_entity)
        """

        # Montando a lista de campos chave (começando pela chave primária)
        key_fields = [self._dto_class.pk_field]

        for key in self._dto_class.fields_map:
            if self._dto_class.fields_map[key].candidate_key:
                key_fields.append(key)

        # Verificando se ocorre o match em algum dos campos chave:
        retornar = False
        for candidate_key in key_fields:
            candidate_key_field = self._dto_class.fields_map[candidate_key]

            if isinstance(id_value, candidate_key_field.expected_type):
                retornar = True
            elif candidate_key_field.expected_type in [int] and isinstance(
                id_value, str
            ):
                id_value = candidate_key_field.expected_type(id_value)
                retornar = True
            elif candidate_key_field.expected_type == uuid.UUID and validate_uuid(
                id_value
            ):
                retornar = True
                id_value = uuid.UUID(id_value)

            if retornar:
                if candidate_key_field.validator is not None:
                    id_value = candidate_key_field.validator(
                        candidate_key_field, id_value
                    )

                # Convertendo o valor para o correspoendente na entity
                entity_key_field = self._convert_to_entity_field(candidate_key)
                converted_values = self._dto_class.custom_convert_value_to_entity(
                    id_value,
                    candidate_key_field,
                    entity_key_field,
                    False,
                    partition_fields,
                )
                if len(converted_values) <= 0:
                    value = self._dto_class.convert_value_to_entity(
                        id_value,
                        candidate_key_field,
                        False,
                        self._entity_class,
                    )
                    converted_values = {entity_key_field: value}

                # Utilizando apenas o valor correspondente ao da chave selecionada
                id_value = converted_values[entity_key_field]

                return (entity_key_field, id_value)

        # Se não pode encontrar uma chave correspondente
        raise ValueError(
            f"Não foi possível identificar o ID recebido com qualquer das chaves candidatas reconhecidas. Valor recebido: {id_value}."
        )

    def _convert_to_entity_fields(
        self,
        fields: Set[str],
        dto_class=None,
        entity_class=None,
        return_hidden_fields: set[str] = None,
    ) -> List[str]:
        """
        Convert a list of fields names to a list of entity fields names.
        """

        if fields is None:
            return None

        # TODO Refatorar para não precisar deste objeto só por conta das propriedades da classe
        # (um decorator na classe, poderia armazenar os fields na mesma, como é feito no DTO)
        if entity_class is None:
            entity = self._entity_class()
        else:
            entity = entity_class()

        # Resolvendo a classe padrão de DTO
        if dto_class is None:
            dto_class = self._dto_class

        acceptable_fields: ty.Set[str] = {
            self._convert_to_entity_field(k, dto_class)
            for k, _ in dto_class.fields_map.items()
            if k in fields
        }
        for v in dto_class.aggregator_fields_map.values():
            acceptable_fields.update(
                {
                    self._convert_to_entity_field(k1, v.expected_type)
                    for k1, v1 in v.expected_type.fields_map.items()
                    if k1 in fields
                }
            )
            pass

        # Adding hidden fields
        if return_hidden_fields is not None:
            acceptable_fields |= return_hidden_fields

        # Removing all the fields not in the entity
        acceptable_fields &= set(entity.__dict__)

        return list(acceptable_fields)

    def _convert_to_entity_field(
        self,
        field: str,
        dto_class=None,
    ) -> str:
        """
        Convert a field name to a entity field name.
        """

        # Resolvendo a classe padrão de DTO
        if dto_class is None:
            dto_class = self._dto_class

        entity_field_name = field
        if dto_class.fields_map[field].entity_field is not None:
            entity_field_name = dto_class.fields_map[field].entity_field

        return entity_field_name

    def _create_entity_filters(
        self, filters: Dict[str, Any]
    ) -> Dict[str, List[Filter]]:
        """
        Converting DTO filters to Entity filters.

        Returns a Dict (indexed by entity field name) of List of Filter.
        """
        if filters is None:
            return None

        # Construindo um novo dict de filtros para controle
        aux_filters = copy.deepcopy(filters)
        fist_run = True

        # Dicionário para guardar os filtros convertidos
        entity_filters = {}
        partial_config = getattr(self._dto_class, "partial_dto_config", None)
        partial_join_alias = (
            self._get_partial_join_alias() if partial_config is not None else None
        )

        # Iterando enquanto houver filtros recebidos, ou derivalos a partir dos filter_aliases
        while len(aux_filters) > 0:
            new_filters = {}

            for filter in aux_filters:
                raw_filter = filter
                is_entity_filter = False
                is_conjunto_filter = False
                is_sql_join_filter = False
                is_one_to_one_filter = False
                is_list_filter = False
                is_list_sql_join_filter = False
                is_length_filter = False
                dto_field = None
                dto_sql_join_field = None
                dto_one_to_one_field = None
                dto_list_field = None
                one_to_one_dto_class = None
                one_to_one_entity_class = None
                list_dto_class = None
                list_entity_class = None
                relation_filter_dto_class = None
                relation_filter_entity_class = None
                relation_parent_field = None
                relation_child_field = None
                relation_join_sql = None
                list_sql_join_field_alias = None
                table_alias = None
                is_partial_extension_field = False
                suffix_operator: FilterOperator | None = None
                suffix_value_mode: str | None = None

                if raw_filter not in self._dto_class.field_filters_map:
                    (
                        filter,
                        suffix_operator,
                        suffix_value_mode,
                    ) = self._resolve_filter_suffix(raw_filter)

                # Recuperando os valores passados nos filtros
                received_value = aux_filters[raw_filter]
                if suffix_operator in [FilterOperator.NULL, FilterOperator.NOT_NULL]:
                    values = [None]
                elif isinstance(received_value, str):
                    values = received_value.split(",")
                else:
                    values = [received_value]

                if len(values) <= 0:
                    # Se não houver valor a filtrar, o filtro é apenas ignorado
                    continue

                # Identificando o tipo de filtro passado
                if (
                    self._dto_class.filter_aliases is not None
                    and raw_filter in self._dto_class.filter_aliases
                    and fist_run
                ):
                    # Verificando se é um alias para outros filtros (o alias aponta para outros filtros,
                    # de acordo com o tipo do dado recebido)
                    filter_aliases = self._dto_class.filter_aliases[raw_filter]

                    # Iterando os tipos definidos para o alias, e verificando se casam com o tipo recebido
                    for type_alias in filter_aliases:
                        relative_field = filter_aliases[type_alias]

                        # Esse obj abaixo é construído artificialmente, com os campos esperados no método validate
                        # Se o validate mudar, tem que refatorar aqui:
                        class OBJ:
                            def __init__(self) -> None:
                                self.expected_type = None
                                self.storage_name = None

                        obj = OBJ()
                        obj.expected_type = type_alias
                        obj.storage_name = raw_filter

                        # Verificando se é possível converter o valor recebido para o tipo definido no alias do filtro
                        try:
                            TypeValidatorUtil.validate(obj, values[0])
                            convertido = True
                        except Exception:
                            convertido = False

                        if convertido:
                            # Se conseguiu converter para o tipo correspondente, se comportará exatamente como um novo
                            # filtro, porém como se tivesse sido passado para o campo correspondente ao tipo:
                            if relative_field not in new_filters:
                                new_filters[relative_field] = received_value
                            else:
                                new_filters[relative_field] = (
                                    f"{new_filters[relative_field]},{received_value}"
                                )
                            break

                        else:
                            # Se não encontrar conseguir converter (até o final, será apenas ignorado)
                            pass

                    continue

                elif filter in self._dto_class.field_filters_map:
                    # Retrieving filter config
                    field_filter = self._dto_class.field_filters_map[filter]
                    aux = self._dto_class.field_filters_map[filter].field_name
                    dto_field = self._dto_class.fields_map[aux]
                    if (
                        partial_config is not None
                        and getattr(dto_field, "name", aux)
                        in partial_config.extension_fields
                    ):
                        is_partial_extension_field = True
                    is_length_filter = field_filter.operator in [
                        FilterOperator.LENGTH_GREATER_OR_EQUAL_THAN,
                        FilterOperator.LENGTH_LESS_OR_EQUAL_THAN,
                    ]

                elif filter == self._dto_class.conjunto_field:
                    is_conjunto_filter = True
                    dto_field = self._dto_class.fields_map[
                        self._dto_class.conjunto_field
                    ]

                elif filter in self._dto_class.fields_map:
                    # NOTE: If something is changed here make sure to check
                    #           if the DTOAggregator part needs to change.

                    # Creating filter config to a DTOField (equals operator)
                    field_filter = DTOFieldFilter(
                        filter,
                        suffix_operator or FilterOperator.EQUALS,
                    )
                    field_filter.set_field_name(filter)
                    dto_field = self._dto_class.fields_map[filter]
                    if (
                        partial_config is not None
                        and getattr(dto_field, "name", filter)
                        in partial_config.extension_fields
                    ):
                        is_partial_extension_field = True

                elif filter in self._dto_class.sql_join_fields_map:
                    # Creating filter config to a DTOSQLJoinField (equals operator)
                    is_sql_join_filter = True
                    field_filter = DTOFieldFilter(
                        filter,
                        suffix_operator or FilterOperator.EQUALS,
                    )
                    field_filter.set_field_name(filter)
                    dto_sql_join_field = self._dto_class.sql_join_fields_map[filter]
                    dto_field = dto_sql_join_field.dto_type.fields_map[
                        dto_sql_join_field.related_dto_field
                    ]

                    # Procurando o table alias
                    for join_query_key in self._dto_class.sql_join_fields_map_to_query:
                        join_query = self._dto_class.sql_join_fields_map_to_query[
                            join_query_key
                        ]
                        if filter in join_query.fields:
                            table_alias = join_query.sql_alias
                elif '.' in filter:
                    dot_index: int = filter.index('.')
                    left_part: str = filter[:dot_index]
                    right_part: str = filter[dot_index + 1 :]
                    if (
                        left_part in self._dto_class.aggregator_fields_map
                        and right_part in self._entity_class().__dict__
                    ):
                        is_entity_filter = True
                        filter = right_part

                        # NOTE: This is a semi copy of the normal field process
                        field_right_part = DTOFieldFilter(right_part)
                        field_right_part.set_field_name(right_part)
                        dto_field = self._dto_class.aggregator_fields_map[
                            left_part
                        ].expected_type.fields_map[right_part]
                        if (
                            partial_config is not None
                            and getattr(dto_field, "name", right_part)
                            in partial_config.extension_fields
                        ):
                            is_partial_extension_field = True
                            pass
                        pass
                    elif left_part in self._dto_class.one_to_one_fields_map:
                        dto_one_to_one_field = self._dto_class.one_to_one_fields_map[
                            left_part
                        ]
                        if (
                            dto_one_to_one_field.entity_relation_owner
                            != EntityRelationOwner.SELF
                        ):
                            continue

                        is_one_to_one_filter = True
                        one_to_one_dto_class = dto_one_to_one_field.expected_type
                        one_to_one_entity_class = dto_one_to_one_field.entity_type
                        table_alias = self._build_one_to_one_filter_alias(left_part)
                        relation_parent_field = dto_one_to_one_field.entity_field
                        relation_child_field = dto_one_to_one_field.relation_field

                        if right_part in one_to_one_dto_class.field_filters_map:
                            field_filter = one_to_one_dto_class.field_filters_map[
                                right_part
                            ]
                            aux = field_filter.field_name
                            dto_field = one_to_one_dto_class.fields_map[aux]
                            is_length_filter = field_filter.operator in [
                                FilterOperator.LENGTH_GREATER_OR_EQUAL_THAN,
                                FilterOperator.LENGTH_LESS_OR_EQUAL_THAN,
                            ]
                        elif right_part in one_to_one_dto_class.fields_map:
                            field_filter = DTOFieldFilter(
                                right_part,
                                suffix_operator or FilterOperator.EQUALS,
                            )
                            field_filter.set_field_name(right_part)
                            dto_field = one_to_one_dto_class.fields_map[right_part]
                        elif right_part in one_to_one_entity_class().__dict__:
                            field_filter = DTOFieldFilter(
                                right_part,
                                suffix_operator or FilterOperator.EQUALS,
                            )
                            field_filter.set_field_name(right_part)
                            is_entity_filter = True
                            filter = right_part
                        else:
                            continue
                    elif left_part in self._dto_class.list_fields_map:
                        dto_list_field = self._dto_class.list_fields_map[left_part]
                        if (
                            dto_list_field.service_name is not None
                            or dto_list_field.entity_type is None
                        ):
                            continue

                        is_list_filter = True
                        list_dto_class = dto_list_field.dto_type
                        list_entity_class = dto_list_field.entity_type
                        table_alias = self._build_list_filter_alias(left_part)
                        relation_filter_dto_class = list_dto_class
                        relation_filter_entity_class = list_entity_class

                        relation_key_field = (
                            dto_list_field.relation_key_field
                            or self._dto_class.pk_field
                        )
                        if relation_key_field is None:
                            continue

                        relation_parent_field = self._convert_to_entity_field(
                            relation_key_field
                        )
                        relation_child_field = dto_list_field.related_entity_field

                        if right_part in list_dto_class.field_filters_map:
                            field_filter = list_dto_class.field_filters_map[
                                right_part
                            ]
                            aux = field_filter.field_name
                            dto_field = list_dto_class.fields_map[aux]
                            is_length_filter = field_filter.operator in [
                                FilterOperator.LENGTH_GREATER_OR_EQUAL_THAN,
                                FilterOperator.LENGTH_LESS_OR_EQUAL_THAN,
                            ]
                        elif right_part in list_dto_class.fields_map:
                            field_filter = DTOFieldFilter(
                                right_part,
                                suffix_operator or FilterOperator.EQUALS,
                            )
                            field_filter.set_field_name(right_part)
                            dto_field = list_dto_class.fields_map[right_part]
                        elif right_part in list_entity_class().__dict__:
                            field_filter = DTOFieldFilter(
                                right_part,
                                suffix_operator or FilterOperator.EQUALS,
                            )
                            field_filter.set_field_name(right_part)
                            is_entity_filter = True
                            filter = right_part
                        elif right_part in list_dto_class.sql_join_fields_map:
                            list_sql_join_field = list_dto_class.sql_join_fields_map[
                                right_part
                            ]
                            if (
                                list_sql_join_field.dto_type is None
                                or list_sql_join_field.entity_type is None
                            ):
                                continue

                            join_dto_class = list_sql_join_field.dto_type
                            join_entity_class = list_sql_join_field.entity_type
                            join_entity = join_entity_class()
                            related_join_field = list_sql_join_field.related_dto_field
                            if related_join_field not in join_dto_class.fields_map:
                                continue

                            field_filter = DTOFieldFilter(
                                right_part,
                                suffix_operator or FilterOperator.EQUALS,
                            )
                            field_filter.set_field_name(related_join_field)
                            dto_field = join_dto_class.fields_map[related_join_field]
                            relation_filter_dto_class = join_dto_class
                            relation_filter_entity_class = join_entity_class
                            is_list_sql_join_filter = True

                            list_sql_join_field_alias = self._build_list_filter_alias(
                                f"{left_part}_{right_part}_filter"
                            )

                            if (
                                list_sql_join_field.entity_relation_owner
                                == EntityRelationOwner.SELF
                            ):
                                if list_sql_join_field.relation_field in list_dto_class.fields_map:
                                    join_self_field = self._convert_to_entity_field(
                                        list_sql_join_field.relation_field,
                                        dto_class=list_dto_class,
                                    )
                                else:
                                    join_self_field = list_sql_join_field.relation_field
                                join_other_field = join_entity.get_pk_field()
                            else:
                                join_self_field = list_entity_class().get_pk_field()
                                if (
                                    list_sql_join_field.relation_field
                                    not in join_dto_class.fields_map
                                ):
                                    continue
                                join_other_field = self._convert_to_entity_field(
                                    list_sql_join_field.relation_field,
                                    dto_class=join_dto_class,
                                )

                            relation_join_sql = (
                                f"{list_sql_join_field.join_type} join "
                                f"{join_entity.get_table_name()} as "
                                f"{list_sql_join_field_alias} on "
                                f"({table_alias}.{join_self_field} = "
                                f"{list_sql_join_field_alias}.{join_other_field})"
                            )
                        else:
                            continue

                # TODO Refatorar para usar um mapa de fields do entity
                elif filter in self._entity_class().__dict__:
                    is_entity_filter = True

                else:
                    # Ignoring not declared filters (or filter for not existent DTOField)
                    continue

                # Resolving entity field name (to filter)
                if (
                    not is_entity_filter
                    and not is_conjunto_filter
                    and not is_sql_join_filter
                    and not is_one_to_one_filter
                    and not is_list_filter
                ):
                    entity_field_name = self._convert_to_entity_field(
                        field_filter.field_name
                    )
                elif is_one_to_one_filter and not is_entity_filter:
                    entity_field_name = self._convert_to_entity_field(
                        field_filter.field_name,
                        dto_class=one_to_one_dto_class,
                    )
                elif is_list_filter and not is_entity_filter:
                    entity_field_name = self._convert_to_entity_field(
                        field_filter.field_name,
                        dto_class=relation_filter_dto_class or list_dto_class,
                    )
                elif is_sql_join_filter:
                    # TODO Verificar se precisa de um if dto_sql_join_field.related_dto_field in dto_sql_join_field.dto_type.fields_map
                    entity_field_name = dto_sql_join_field.dto_type.fields_map[
                        dto_sql_join_field.related_dto_field
                    ].get_entity_field_name()
                else:
                    entity_field_name = filter

                # Creating entity filters (one for each value - separated by comma)
                for value in values:
                    if isinstance(value, str):
                        value = value.strip()
                    value = self._apply_filter_value_mode(value, suffix_value_mode)

                    # Resolvendo as classes de DTO e Entity
                    aux_dto_class = self._dto_class
                    aux_entity_class = self._entity_class

                    if is_sql_join_filter:
                        aux_dto_class = dto_sql_join_field.dto_type
                        aux_entity_class = dto_sql_join_field.entity_type
                    elif is_one_to_one_filter:
                        aux_dto_class = one_to_one_dto_class
                        aux_entity_class = one_to_one_entity_class
                    elif is_list_filter:
                        aux_dto_class = relation_filter_dto_class or list_dto_class
                        aux_entity_class = relation_filter_entity_class or list_entity_class

                    # Convertendo os valores para o formato esperado no entity
                    if (
                        not is_entity_filter
                        and not is_sql_join_filter
                        and not is_one_to_one_filter
                        and not is_list_filter
                        and not is_length_filter
                    ):
                        converted_values = aux_dto_class.custom_convert_value_to_entity(
                            value,
                            dto_field,
                            entity_field_name,
                            False,
                            aux_filters,
                        )
                        if len(converted_values) <= 0:
                            value = aux_dto_class.convert_value_to_entity(
                                value,
                                dto_field,
                                False,
                                aux_entity_class,
                            )
                            converted_values = {entity_field_name: value}

                    elif (
                        not is_entity_filter
                        and (is_one_to_one_filter or is_list_filter)
                        and not is_length_filter
                    ):
                        converted_values = aux_dto_class.custom_convert_value_to_entity(
                            value,
                            dto_field,
                            entity_field_name,
                            False,
                            aux_filters,
                        )
                        if len(converted_values) <= 0:
                            value = aux_dto_class.convert_value_to_entity(
                                value,
                                dto_field,
                                False,
                                aux_entity_class,
                            )
                            converted_values = {entity_field_name: value}
                    else:
                        converted_values = {entity_field_name: value}

                    # Tratando cada valor convertido
                    for entity_field in converted_values:
                        converted_value = converted_values[entity_field]

                        if (
                            not is_entity_filter
                            and not is_conjunto_filter
                            and not is_sql_join_filter
                            and not is_one_to_one_filter
                            and not is_list_filter
                        ):
                            alias = None
                            if is_partial_extension_field:
                                alias = partial_join_alias
                                if entity_field != entity_field_name:
                                    alias = None
                            entity_filter = Filter(
                                field_filter.operator, converted_value, alias
                            )
                        elif is_list_filter:
                            entity_filter = Filter(
                                field_filter.operator,
                                converted_value,
                                table_alias,
                                relation_mode="exists",
                                relation_table=list_entity_class().get_table_name(),
                                relation_parent_field=relation_parent_field,
                                relation_child_field=relation_child_field,
                                relation_join_sql=relation_join_sql,
                            )
                        elif is_one_to_one_filter:
                            entity_filter = Filter(
                                field_filter.operator,
                                converted_value,
                                table_alias,
                                relation_mode="exists",
                                relation_table=one_to_one_entity_class().get_table_name(),
                                relation_parent_field=relation_parent_field,
                                relation_child_field=relation_child_field,
                            )
                        elif is_sql_join_filter:
                            entity_filter = Filter(
                                field_filter.operator, converted_value, table_alias
                            )
                        else:
                            entity_filter = Filter(
                                suffix_operator or FilterOperator.EQUALS,
                                converted_value,
                            )

                        # Storing filter in dict
                        stored_entity_field = entity_field
                        if (
                            is_list_sql_join_filter
                            and list_sql_join_field_alias is not None
                            and "." not in stored_entity_field
                        ):
                            stored_entity_field = (
                                f"{list_sql_join_field_alias}.{stored_entity_field}"
                            )

                        filter_list = entity_filters.setdefault(stored_entity_field, [])
                        filter_list.append(entity_filter)

            # Ajustando as variáveis de controle
            fist_run = False
            aux_filters = {}
            aux_filters.update(new_filters)

        return entity_filters










    def _make_fields_from_dto(self, dto: DTOBase) -> FieldsTree:
        fields_tree: FieldsTree = {"root": set()}

        for field in dto.fields_map:
            if field in dto.__dict__:
                fields_tree["root"].add(field)

        for list_field in dto.list_fields_map:
            if list_field not in dto.__dict__:
                continue

            list_dto = getattr(dto, list_field)
            if not list_dto:
                continue

            fields_tree["root"].add(list_field)
            fields_tree[list_field] = self._make_fields_from_dto(list_dto[0])

        return fields_tree

    def entity_exists(
        self,
        entity: EntityBase,
        entity_filters: Dict[str, List[Filter]],
    ):
        # Getting values
        entity_pk_field = entity.get_pk_field()
        entity_pk_value = getattr(entity, entity_pk_field)

        if entity_pk_value is None:
            return False

        # Searching entity in DB
        try:
            self._dao.get(
                entity_pk_field,
                entity_pk_value,
                [entity.get_pk_field()],
                entity_filters,
            )
        except NotFoundException:
            return False

        return True
