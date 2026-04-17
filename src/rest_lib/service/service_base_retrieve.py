import typing as ty
import warnings

from typing import Any, Dict, List, Set

from rest_lib.dao.dao_base import DAOBase
from rest_lib.descriptor.dto_one_to_one_field import DTOOneToOneField
from rest_lib.descriptor.dto_left_join_field import (
    DTOLeftJoinField,
    EntityRelationOwner,
    LeftJoinQuery,
)
from rest_lib.descriptor.dto_object_field import DTOObjectField
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.filter import Filter
from rest_lib.exception import (
    DTOListFieldConfigException,
    NotFoundException,
)
from rest_lib.settings import get_logger
from rest_lib.util.fields_util import (
    FieldsTree,
    clone_fields_tree,
    extract_child_tree,
    merge_fields_tree,
    normalize_fields_tree,
)
from rest_lib.util.join_aux import JoinAux

from .service_base_partial_of import ServiceBasePartialOf


class ServiceBaseRetrieve(ServiceBasePartialOf):
    def _resolving_fields(self, fields: FieldsTree) -> FieldsTree:
        """
        Verifica os fields recebidos, garantindo que os campos de resumo (incluindo os
        configurados nos relacionamentos) sejam considerados.
        """

        result = normalize_fields_tree(fields)
        merge_fields_tree(result, self._dto_class.build_default_fields_tree())

        # Tratamento especial para campos agregadores
        for field_name, descriptor in self._dto_class.aggregator_fields_map.items():
            if field_name not in result["root"]:
                continue

            result["root"] |= descriptor.expected_type.resume_fields

            if field_name not in result:
                continue

            child_tree = result.pop(field_name)
            if isinstance(child_tree, dict):
                result["root"] |= child_tree.get("root", set())

                for nested_field, nested_tree in child_tree.items():
                    if nested_field == "root":
                        continue

                    existing = result.get(nested_field)
                    if not isinstance(existing, dict):
                        result[nested_field] = clone_fields_tree(nested_tree)
                    else:
                        merge_fields_tree(existing, nested_tree)

        return result

    def _add_overide_data_filters(self, all_filters):
        if (
            self._dto_class.data_override_group is not None
            and self._dto_class.data_override_fields is not None
        ):
            for field in self._dto_class.data_override_fields:
                if field in self._dto_class.fields_map:
                    null_value = self._dto_class.fields_map[field].get_null_value()
                    if field in all_filters:
                        all_filters[field] = f"{all_filters[field]},{null_value}"
                    else:
                        all_filters[field] = f"{null_value}"

    def _group_by_override_data(self, dto_list):

        if (
            self._dto_class.data_override_group is not None
            and self._dto_class.data_override_fields is not None
        ):
            grouped_dto_list = {}
            reversed_data_override_fields = reversed(
                self._dto_class.data_override_fields
            )
            for dto in dto_list:
                ## Resolvendo o ID do grupo
                group_id = ""
                for field in self._dto_class.data_override_group:
                    if field in self._dto_class.fields_map:
                        group_id += f"{getattr(dto, field)}_"

                ## Guardando o DTO mais completo do grupo
                if group_id not in grouped_dto_list:
                    grouped_dto_list[group_id] = dto
                else:
                    ### Testa se o novo DTO é mais específico do que o já guardado, e o troca, caso positivo
                    last_dto_group = grouped_dto_list[group_id]
                    for field in reversed_data_override_fields:
                        if field in self._dto_class.fields_map:
                            dto_value = getattr(dto, field)
                            last_dto_value = getattr(last_dto_group, field)
                            null_value = self._dto_class.fields_map[
                                field
                            ].get_null_value()

                            if (
                                dto_value is not None
                                and null_value is not None
                                and dto_value != null_value
                                and (
                                    last_dto_value is None
                                    or last_dto_value == null_value
                                )
                            ):
                                grouped_dto_list[group_id] = dto

            ## Atualizando a lista de DTOs
            dto_list = list(grouped_dto_list.values())

        return dto_list

    def _retrieve_related_lists(
        self,
        dto_list: List[DTOBase],
        fields: FieldsTree,
        expands: FieldsTree,
    ):

        # TODO Controlar profundidade?!
        if not dto_list:
            return

        from .service_base import ServiceBase

        for master_dto_attr, list_field in self._dto_class.list_fields_map.items():
            if master_dto_attr not in fields["root"]:
                continue

            # Coletar todos os valores de chave relacionados dos DTOs
            relation_key_field = self._dto_class.pk_field
            if list_field.relation_key_field is not None:
                relation_key_field = list_field.relation_key_field

            # Mapeia valor da chave -> lista de DTOs que possuem esse valor
            key_to_dtos = {}
            for dto in dto_list:
                relation_filter_value = getattr(dto, relation_key_field, None)
                if relation_filter_value is not None:
                    key_to_dtos.setdefault(relation_filter_value, []).append(dto)
                else:
                    setattr(dto, master_dto_attr, [])

            if not key_to_dtos:
                continue

            # Instancia o service
            if list_field.service_name is not None:
                service = self._injector_factory.get_service_by_name(
                    list_field.service_name
                )
            else:
                service = ServiceBase(
                    self._injector_factory,
                    DAOBase(
                        self._injector_factory.db_adapter(),
                        list_field.entity_type,
                    ),
                    list_field.dto_type,
                    list_field.entity_type,
                )

            # Monta o filtro IN para buscar todos os relacionados de uma vez
            filters = {
                list_field.related_entity_field: ",".join(
                    [str(key) for key in key_to_dtos]
                )
            }

            # Campos de particionamento: se existirem, só faz sentido se todos os DTOs tiverem o mesmo valor
            # (caso contrário, teria que quebrar em vários queries)
            # Aqui, só trata se todos tiverem o mesmo valor para cada campo de partição
            for field in self._dto_class.partition_fields:
                if field in list_field.dto_type.partition_fields:
                    partition_values = set(
                        getattr(dto, field, None) for dto in dto_list
                    )
                    partition_values.discard(None)
                    if len(partition_values) == 1:
                        filters[field] = partition_values.pop()
                    # Se houver mais de um valor, teria que quebrar em vários queries (não tratado aqui)

            # Resolvendo os fields da entidade aninhada
            fields_to_list = extract_child_tree(fields, master_dto_attr)
            expands_to_list = extract_child_tree(expands, master_dto_attr)

            # Busca todos os relacionados de uma vez
            related_dto_list = service.list(
                None,
                None,
                fields_to_list,
                None,
                filters,
                return_hidden_fields=set([list_field.related_entity_field]),
                expands=expands_to_list,
            )

            # Agrupa os relacionados por chave
            related_map = {}
            for related_dto in related_dto_list:
                relation_key = str(
                    related_dto.return_hidden_fields.get(
                        list_field.related_entity_field, None
                    )
                )
                if relation_key is not None:
                    related_map.setdefault(relation_key, []).append(related_dto)

            # Seta nos DTOs principais
            for key, dtos in key_to_dtos.items():
                related = related_map.get(str(key), [])
                for dto in dtos:
                    setattr(dto, master_dto_attr, related)

    def _resolve_sql_join_fields(
        self,
        fields: Set[str],
        entity_filters: Dict[str, List[Filter]],
        partial_join_fields: Set[str] = None,
    ) -> List[JoinAux]:
        """
        Analisa os campos de jooin solicitados, e monta uma lista de objetos
        para auxiliar o DAO na construção da query
        """

        # Criando o objeto de retorno
        joins_aux: List[JoinAux] = []

        # Iterando os campos de join configurados, mas só considerando os solicitados (ou de resumo)
        for join_field_map_to_query_key in self._dto_class.sql_join_fields_map_to_query:
            join_field_map_to_query = self._dto_class.sql_join_fields_map_to_query[
                join_field_map_to_query_key
            ]

            used_join_fields = set()

            # Verificando se um dos campos desse join será usado
            for join_field in join_field_map_to_query.fields:
                # Recuperando o nome do campo, na entity
                entity_join_field = join_field_map_to_query.related_dto.fields_map[
                    self._dto_class.sql_join_fields_map[join_field].related_dto_field
                ].get_entity_field_name()

                if join_field in fields or entity_join_field in entity_filters:
                    relate_join_field = self._dto_class.sql_join_fields_map[
                        join_field
                    ].related_dto_field
                    used_join_fields.add(relate_join_field)

            # Pulando esse join (se não for usado)
            if len(used_join_fields) <= 0:
                continue

            # Construindo o objeto auxiliar do join
            join_aux = JoinAux()

            # Resolvendo os nomes dos fields da entidade relacionada
            join_entity_fields = self._convert_to_entity_fields(
                fields=used_join_fields,
                dto_class=join_field_map_to_query.related_dto,
                entity_class=join_field_map_to_query.related_entity,
            )

            join_aux.fields = join_entity_fields

            # Resolvendo tabela, tipo de join e alias
            other_entity = join_field_map_to_query.related_entity()
            join_aux.table = other_entity.get_table_name()
            join_aux.type = join_field_map_to_query.join_type
            join_aux.alias = join_field_map_to_query.sql_alias

            # Resovendo os campos usados no join
            if (
                join_field_map_to_query.entity_relation_owner
                == EntityRelationOwner.SELF
            ):
                join_aux.self_field = self._dto_class.fields_map[
                    join_field_map_to_query.relation_field
                ].get_entity_field_name()
                join_aux.other_field = other_entity.get_pk_field()
            else:
                join_aux.self_field = self._entity_class().get_pk_field()
                join_aux.other_field = join_field_map_to_query.related_dto.fields_map[
                    join_field_map_to_query.relation_field
                ].get_entity_field_name()

            joins_aux.append(join_aux)

        for field_name, oto_field in self._dto_class.one_to_one_fields_map.items():
            if oto_field.entity_relation_owner != EntityRelationOwner.SELF:
                continue

            alias = self._build_one_to_one_filter_alias(field_name)
            join_required = False
            if entity_filters is not None:
                for filter_list in entity_filters.values():
                    for condiction in filter_list:
                        if (
                            condiction.table_alias == alias
                            and condiction.relation_mode != "exists"
                        ):
                            join_required = True
                            break
                    if join_required:
                        break

            if not join_required:
                continue

            join_aux = JoinAux()
            other_entity = oto_field.entity_type()
            join_aux.table = other_entity.get_table_name()
            join_aux.type = "inner"
            join_aux.alias = alias
            join_aux.fields = []
            join_aux.self_field = oto_field.entity_field
            join_aux.other_field = oto_field.relation_field
            joins_aux.append(join_aux)

        partial_config = getattr(self._dto_class, "partial_dto_config", None)
        partial_entity_config = getattr(
            self._entity_class, "partial_entity_config", None
        )
        if partial_config is not None and partial_entity_config is not None:
            alias = self._get_partial_join_alias()
            join_fields_needed: Set[str] = set(partial_join_fields or set())
            join_required = len(join_fields_needed) > 0

            if entity_filters is not None and not join_required:
                for filter_list in entity_filters.values():
                    for condiction in filter_list:
                        if condiction.table_alias == alias:
                            join_required = True
                            break
                    if join_required:
                        break

            if join_required:
                join_aux = JoinAux()
                join_aux.table = partial_entity_config.extension_table_name
                join_aux.type = "inner"
                join_aux.alias = alias
                join_aux.fields = list(join_fields_needed) if join_fields_needed else []

                try:
                    join_aux.self_field = self._convert_to_entity_field(
                        partial_config.related_entity_field,
                        dto_class=partial_config.parent_dto,
                    )
                except KeyError:
                    join_aux.self_field = partial_config.related_entity_field

                join_aux.other_field = partial_config.relation_field

                joins_aux.append(join_aux)

        return joins_aux

    def _retrieve_left_join_fields(
        self,
        dto_list: List[DTOBase],
        fields: FieldsTree,
        partition_fields: Dict[str, Any],
    ):
        warnings.warn(
            "DTOLeftJoinField está depreciado e será removido em breve.",
            DeprecationWarning,
        )

        from .service_base import ServiceBase

        # Tratando cada dto recebido
        for dto in dto_list:
            # Tratando cada tipo de entidade relacionada
            left_join_fields_map_to_query = getattr(
                dto.__class__, "left_join_fields_map_to_query", {}
            )
            for left_join_query_key in left_join_fields_map_to_query:
                left_join_query: LeftJoinQuery = left_join_fields_map_to_query[
                    left_join_query_key
                ]

                # Verificando os fields de interesse
                fields_necessarios = set()
                for field in left_join_query.fields:
                    if field in fields["root"]:
                        fields_necessarios.add(field)

                # Se nenhum dos fields registrados for pedido, ignora esse relacioanemtno
                if len(fields_necessarios) <= 0:
                    continue

                # Getting related service instance
                # TODO Refatorar para suportar services customizados
                service = ServiceBase(
                    self._injector_factory,
                    DAOBase(
                        self._injector_factory.db_adapter(),
                        left_join_query.related_entity,
                    ),
                    left_join_query.related_dto,
                    left_join_query.related_entity,
                )

                # Montando a lista de campos a serem recuperados na entidade relacionada
                related_fields = set()
                for left_join_field in left_join_query.left_join_fields:
                    # Ignorando os campos que não estejam no retorno da query
                    if left_join_field.name not in fields_necessarios:
                        continue

                    related_fields.add(left_join_field.related_dto_field)

                related_fields = {"root": related_fields}

                # Verificando quem é o dono do relacionamento, e recuperando o DTO relcaionado
                # da forma correspondente
                related_dto = None
                if left_join_query.entity_relation_owner == EntityRelationOwner.OTHER:
                    # Checking if pk_field exists
                    if self._dto_class.pk_field is None:
                        raise DTOListFieldConfigException(
                            f"PK field not found in class: {self._dto_class}"
                        )

                    # Montando os filtros para recuperar o objeto relacionado
                    related_filters = {
                        left_join_query.left_join_fields[0].relation_field: getattr(
                            dto, self._dto_class.pk_field
                        )
                    }

                    # Recuperando a lista de DTOs relacionados (com um único elemento; limit=1)
                    related_dto = service.list(
                        None,
                        1,
                        related_fields,
                        None,
                        related_filters,
                    )
                    if len(related_dto) > 0:
                        related_dto = related_dto[0]
                    else:
                        related_dto = None

                elif left_join_query.entity_relation_owner == EntityRelationOwner.SELF:
                    # Checking if pk_field exists
                    if getattr(left_join_query.related_dto, "pk_field") is None:
                        raise DTOListFieldConfigException(
                            f"PK field not found in class: {left_join_query.related_dto}"
                        )

                    # Recuperando a PK da entidade relacionada
                    related_pk = getattr(
                        dto, left_join_query.left_join_fields[0].relation_field
                    )

                    if related_pk is None:
                        continue

                    # Recuperando o DTO relacionado
                    related_dto = service.get(
                        related_pk, partition_fields, related_fields
                    )
                else:
                    raise Exception(
                        f"Tipo de relacionamento (left join) não identificado: {left_join_query.entity_relation_owner}."
                    )

                # Copiando os campos necessários
                for field in fields_necessarios:
                    # Recuperando a configuração do campo left join
                    left_join_field: DTOLeftJoinField = dto.left_join_fields_map[field]

                    if related_dto is not None:
                        # Recuperando o valor da propriedade no DTO relacionado
                        field_value = getattr(
                            related_dto, left_join_field.related_dto_field
                        )

                        # Gravando o valor no DTO de interesse
                        setattr(dto, field, field_value)

    def _retrieve_object_fields_old(
        self,
        dto_list: List[DTOBase],
        fields: FieldsTree,
        partition_fields: Dict[str, Any],
    ):
        from .service_base import ServiceBase

        # Tratando cada dto recebido
        for dto in dto_list:
            for key in dto.object_fields_map:
                # Verificando se o campo está no retorno
                if key not in fields["root"]:
                    continue

                object_field: DTOObjectField = dto.object_fields_map[key]

                if object_field.entity_type is None:
                    continue

                service = ServiceBase(
                    self._injector_factory,
                    DAOBase(
                        self._injector_factory.db_adapter(),
                        object_field.entity_type,
                    ),
                    object_field.expected_type,
                    object_field.entity_type,
                )

                if object_field.entity_relation_owner == EntityRelationOwner.OTHER:
                    # Checking if pk_field exists
                    if self._dto_class.pk_field is None:
                        raise DTOListFieldConfigException(
                            f"PK field not found in class: {self._dto_class}"
                        )

                    # Montando os filtros para recuperar o objeto relacionado
                    related_filters = {
                        object_field.relation_field: getattr(
                            dto, self._dto_class.pk_field
                        )
                    }

                    # Recuperando a lista de DTOs relacionados (com um único elemento; limit=1)
                    related_dto = service.list(
                        None,
                        1,
                        extract_child_tree(fields, key),
                        None,
                        related_filters,
                    )
                    if len(related_dto) > 0:
                        field = related_dto[0]
                    else:
                        field = None

                    setattr(dto, key, field)

                elif object_field.entity_relation_owner == EntityRelationOwner.SELF:
                    if getattr(dto, object_field.relation_field) is not None:
                        try:
                            field = service.get(
                                getattr(dto, object_field.relation_field),
                                partition_fields,
                                extract_child_tree(fields, key),
                            )
                        except NotFoundException:
                            field = None

                        setattr(dto, key, field)

    def _retrieve_object_fields(
        self,
        dto_list: List[DTOBase],
        fields: FieldsTree,
        partition_fields: Dict[str, Any],
    ):
        """
        Versão otimizada do _retrieve_object_fields_keyson que faz buscas em lote
        ao invés de consultas individuais para cada DTO.
        """
        if not dto_list:
            return

        from .service_base import ServiceBase

        # Processando cada tipo de campo de objeto
        for key in self._dto_class.object_fields_map:
            # Verificando se o campo está no retorno
            if key not in fields["root"]:
                continue

            object_field: DTOObjectField = self._dto_class.object_fields_map[key]

            if object_field.entity_type is None:
                continue

            # Instanciando o service uma vez só para este tipo de campo
            service = ServiceBase(
                self._injector_factory,
                DAOBase(
                    self._injector_factory.db_adapter(),
                    object_field.entity_type,
                ),
                object_field.expected_type,
                object_field.entity_type,
            )

            if object_field.entity_relation_owner == EntityRelationOwner.OTHER:
                # Checking if pk_field exists
                if self._dto_class.pk_field is None:
                    raise DTOListFieldConfigException(
                        f"PK field not found in class: {self._dto_class}"
                    )

                # Coletando todas as chaves primárias dos DTOs para buscar de uma vez
                keys_to_fetch = set()
                for dto in dto_list:
                    pk_value = getattr(dto, self._dto_class.pk_field)
                    if pk_value is not None:
                        keys_to_fetch.add(pk_value)

                if not keys_to_fetch:
                    continue

                # Montando filtro para buscar todos os objetos relacionados de uma vez
                related_filters = {
                    object_field.relation_field: ",".join(str(k) for k in keys_to_fetch)
                }

                # Recuperando todos os DTOs relacionados de uma vez
                related_dto_list = service.list(
                    None,
                    None,
                    extract_child_tree(fields, key),
                    None,
                    related_filters,
                    return_hidden_fields=set([object_field.relation_field]),
                )

                # Criando mapa de chave -> DTO relacionado
                related_map = {}
                for related_dto in related_dto_list:
                    relation_key = str(
                        related_dto.return_hidden_fields.get(
                            object_field.relation_field, None
                        )
                    )
                    if relation_key is not None:
                        related_map[relation_key] = related_dto

                # Atribuindo os objetos relacionados nos DTOs originais
                for dto in dto_list:
                    pk_value = str(getattr(dto, self._dto_class.pk_field))
                    related_dto = related_map.get(pk_value)
                    setattr(dto, key, related_dto)

            elif object_field.entity_relation_owner == EntityRelationOwner.SELF:
                # FIXME A recuperação do nome do field do DTO só é necessária,
                # porque o relcionamento aponta para o nome da entity (isso deve ser mudado no futuro)
                dto_field_name = None
                for field, dto_field in self._dto_class.fields_map.items():
                    dto_entity_field_name = field
                    if dto_field.entity_field:
                        dto_entity_field_name = dto_field.entity_field

                    if object_field.relation_field == dto_entity_field_name:
                        dto_field_name = field
                        break

                if not dto_field_name:
                    get_logger().warning(
                        f"Campo de relacionamento do tipo DTOObjectField.SELF ({object_field.relation_field}) não encontrado do DTO: {self._dto_class}"
                    )
                    continue

                # Coletando todas as chaves de relacionamento para buscar de uma vez
                keys_to_fetch = set()
                for dto in dto_list:
                    relation_value = getattr(dto, dto_field_name)
                    if relation_value is not None:
                        keys_to_fetch.add(relation_value)

                if not keys_to_fetch:
                    continue

                # Montando filtro para buscar todos os objetos relacionados de uma vez
                related_filters = {
                    object_field.expected_type.pk_field: ",".join(
                        str(k) for k in keys_to_fetch
                    )
                }

                # Recuperando todos os DTOs relacionados de uma vez
                related_dto_list = service.list(
                    None,
                    None,
                    extract_child_tree(fields, key),
                    None,
                    related_filters,
                )

                # Criando mapa de chave -> DTO relacionado
                related_map = {}
                for related_dto in related_dto_list:
                    pk_field = getattr(related_dto.__class__, "pk_field")
                    pk_value = str(getattr(related_dto, pk_field))
                    if pk_value is not None:
                        related_map[pk_value] = related_dto

                # Atribuindo os objetos relacionados nos DTOs originais
                for dto in dto_list:
                    relation_value = str(getattr(dto, dto_field_name))
                    related_dto = related_map.get(relation_value)
                    setattr(dto, key, related_dto)

    def _retrieve_one_to_one_fields(
        self,
        dto_list: ty.List[ty.Union[DTOBase, EntityBase]],
        fields: ty.Dict[str, ty.Set[str]],
        expands: FieldsTree,
        partition_fields: ty.Dict[str, ty.Any],
    ) -> None:
        if len(dto_list) == 0:
            return

        from .service_base import ServiceBase

        oto_field: DTOOneToOneField
        for key, oto_field in self._dto_class.one_to_one_fields_map.items():
            if key not in fields["root"] or key not in expands["root"]:
                continue

            if oto_field.entity_relation_owner != EntityRelationOwner.SELF:
                continue

            service = ServiceBase(
                self._injector_factory,
                DAOBase(
                    self._injector_factory.db_adapter(),
                    oto_field.entity_type,
                ),
                oto_field.expected_type,
                oto_field.entity_type,
            )

            field_name: str = oto_field.entity_field

            keys_to_fetch: ty.Set[str] = {
                getattr(dto, field_name)
                for dto in dto_list
                if getattr(dto, field_name) is not None
            }

            if len(keys_to_fetch) == 0:
                continue

            relation_field: str = oto_field.relation_field

            related_filters: ty.Dict[str, str] = {
                relation_field: ",".join(str(k) for k in keys_to_fetch)
            }

            local_expands: ty.Optional[FieldsTree] = None
            if key in expands:
                local_expands = extract_child_tree(expands, key)
                pass

            local_fields: FieldsTree = {"root": set()}
            if key in fields:
                local_fields = extract_child_tree(fields, key)
                pass

            related_dto_list: ty.List[DTOBase] = service.list(
                after=None,
                limit=None,
                fields=local_fields,
                order_fields=None,
                filters=related_filters,
                search_query=None,
                return_hidden_fields=set([relation_field]),
                expands=local_expands,
            )

            related_map: ty.Dict[str, DTOBase] = {
                str(x.return_hidden_fields.get(relation_field)): x
                for x in related_dto_list
            }
            # NOTE: I'm assuming relation_field of x will never be NULL, because
            #           to be NULL would mean to not have an identifier.

            for dto in dto_list:
                orig_val: str = str(getattr(dto, field_name))
                if orig_val is None:
                    setattr(dto, field_name, None)
                    continue

                if orig_val not in related_map:
                    # NOTE: Separating from when orig_val is None because it
                    #           probably should be an error when the field has
                    #           a value but said value does not exist on the
                    #           related table.
                    setattr(dto, field_name, None)
                    continue

                setattr(dto, field_name, related_map[orig_val])
