import abc
import copy
import typing as ty

from rest_lib.descriptor.function_field import FunctionField

if ty.TYPE_CHECKING:
    from rest_lib.dto.dto_base import DTOBase
    from rest_lib.descriptor.dto_field import DTOField
    from rest_lib.descriptor.dto_list_field import DTOListField
    from rest_lib.descriptor.dto_object_field import DTOObjectField
    from rest_lib.descriptor.dto_one_to_one_field import DTOOneToOneField


class FunctionTypeBase(abc.ABC):
    """
    Classe base para todos os tipos usados em funções PL/PGSQL (insert/update),
    mantendo o contrato esperado pelo DAO para identificar campos e referências.
    """

    fields_map: ty.Dict[str, FunctionField] = {}
    type_name: str = ""
    function_name: str = ""
    pk_field_name: ty.Optional[str] = None
    dto_lookup_attribute: str = "function_field_lookup"
    _dto_function_mapping_cache: ty.Dict[
        ty.Type["DTOBase"], ty.Dict[str, ty.Tuple[str, ty.Any]]
    ] = {}

    @classmethod
    def get_fields_map(cls) -> ty.Dict[str, FunctionField]:
        if not hasattr(cls, "fields_map"):
            raise NotImplementedError(
                f"fields_map não definido em {cls.__name__}"
            )
        return cls.fields_map

    def get_type_name(self) -> str:
        if not hasattr(self.__class__, "type_name"):
            raise NotImplementedError(
                f"type_name não definido em {self.__class__.__name__}"
            )
        return self.__class__.type_name

    def get_function_name(self) -> str:
        if not hasattr(self.__class__, "function_name"):
            raise NotImplementedError(
                f"function_name não definido em {self.__class__.__name__}"
            )
        return self.__class__.function_name

    @classmethod
    def get_pk_field_name(cls) -> ty.Optional[str]:
        """
        Retorna o nome do campo marcado como pk no FunctionType, se houver.
        """
        return getattr(cls, "pk_field_name", None)

    @classmethod
    def build_from_params(
        cls,
        params: dict[str, ty.Any],
        id_value: ty.Any = None,
    ) -> "FunctionTypeBase":
        """
        Constrói uma instância preenchida a partir de um dicionário de parâmetros,
        opcionalmente preenchendo o campo pk com id_value.
        """
        instance = cls()
        fields_map = cls.get_fields_map()

        pk_field = cls.get_pk_field_name()
        if id_value is not None:
            if pk_field is None:
                raise ValueError(
                    f"FunctionType '{cls.__name__}' não possui campo pk configurado."
                )
            setattr(instance, pk_field, id_value)

        for key, value in params.items():
            if key in fields_map:
                setattr(instance, key, value)
                continue
            for field_name, descriptor in fields_map.items():
                if descriptor.get_type_field_name() == key:
                    setattr(instance, field_name, value)
                    break

        return instance

    @classmethod
    def get_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        cache = getattr(cls, "_dto_function_mapping_cache", None)
        if cache is None:
            cache = {}
            setattr(cls, "_dto_function_mapping_cache", cache)

        if dto_class not in cache:
            cache[dto_class] = cls._build_function_mapping(dto_class)

        return cache[dto_class]

    @classmethod
    def _build_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        lookup = getattr(dto_class, cls.dto_lookup_attribute, None)
        if not lookup:
            raise ValueError(
                f"DTO '{dto_class.__name__}' não possui '{cls.dto_lookup_attribute}' configurado."
            )

        fields_map = getattr(cls, "fields_map", {})
        mapping: ty.Dict[str, ty.Tuple[str, ty.Any]] = {}

        for field_name, function_descriptor in fields_map.items():
            if field_name not in lookup:
                inferred_mapping = cls._infer_field_mapping(
                    dto_class,
                    field_name,
                )
                if inferred_mapping is None:
                    inferred_mapping = cls._infer_relation_mapping(
                        dto_class,
                        field_name,
                        function_descriptor,
                    )
                if inferred_mapping is None:
                    inferred_mapping = cls._infer_external_mapping(
                        function_descriptor
                    )
                if inferred_mapping is None:
                    raise ValueError(
                        f"O campo '{field_name}' do FunctionType '{cls.__name__}' não existe no DTO '{dto_class.__name__}'."
                    )
                mapping[field_name] = inferred_mapping
                continue

            mapping[field_name] = cls._override_relation_mapping(
                lookup[field_name],
                function_descriptor,
            )

        return mapping

    @classmethod
    def _infer_field_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
        field_name: str,
    ) -> ty.Optional[ty.Tuple[str, ty.Any]]:
        """
        Tenta localizar um campo do FunctionType fora do lookup direto do DTO.

        Esse fallback cobre três cenários recorrentes:
        - aliases físicos vindos de `entity_field`;
        - nomes de campos específicos de função (`insert/update_function_field`);
        - campos expostos por aggregators, retornando um caminho pontilhado.
        """
        operation = cls._get_lookup_operation()
        if operation is None:
            return None

        for dto_field_name, descriptor in getattr(dto_class, "fields_map", {}).items():
            candidate_names = {dto_field_name}

            entity_field = getattr(descriptor, "entity_field", None)
            if entity_field:
                candidate_names.add(entity_field)

            get_function_field_name = getattr(
                descriptor,
                "get_function_field_name",
                None,
            )
            if callable(get_function_field_name):
                candidate_names.add(get_function_field_name(operation))

            if field_name in candidate_names:
                return (dto_field_name, descriptor)

        for aggregator_name, aggregator_descriptor in getattr(
            dto_class, "aggregator_fields_map", {}
        ).items():
            aggregator_dto = getattr(aggregator_descriptor, "expected_type", None)
            if aggregator_dto is None:
                continue

            for dto_field_name, descriptor in getattr(
                aggregator_dto, "fields_map", {}
            ).items():
                dotted_name = f"{aggregator_name}.{dto_field_name}"
                candidate_names = {dto_field_name, dotted_name}

                entity_field = getattr(descriptor, "entity_field", None)
                if entity_field:
                    candidate_names.add(entity_field)

                get_function_field_name = getattr(
                    descriptor,
                    "get_function_field_name",
                    None,
                )
                if callable(get_function_field_name):
                    candidate_names.add(get_function_field_name(operation))

                if field_name in candidate_names:
                    return (dotted_name, descriptor)

        return None

    @classmethod
    def _override_relation_mapping(
        cls,
        current_mapping: ty.Tuple[str, ty.Any],
        function_descriptor: FunctionField,
    ) -> ty.Tuple[str, ty.Any]:
        dto_field_name, current_descriptor = current_mapping
        related_type = getattr(function_descriptor, "related_type", None)
        operation = cls._get_lookup_operation()

        if related_type is None or operation not in {"insert", "update"}:
            return current_mapping

        inferred_descriptor = copy.deepcopy(current_descriptor)
        if operation == "update":
            setattr(inferred_descriptor, "update_function_type", related_type)
        else:
            setattr(inferred_descriptor, "insert_function_type", related_type)

        return (dto_field_name, inferred_descriptor)

    @classmethod
    def _infer_relation_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
        field_name: str,
        function_descriptor: FunctionField,
    ) -> ty.Optional[ty.Tuple[str, ty.Any]]:
        """
        Rebuilds missing relation mappings when the DTO inherited the relation
        descriptor but not the explicit insert/update FunctionType metadata.

        This keeps FunctionType definitions as the source of truth for relation
        payloads while remaining backward compatible with DTOs compiled from
        partial extensions.
        """
        related_type = getattr(function_descriptor, "related_type", None)
        if related_type is None:
            return None

        operation = cls._get_lookup_operation()
        if operation not in {"insert", "update"}:
            return None

        for relation_map_name in (
            "list_fields_map",
            "object_fields_map",
            "one_to_one_fields_map",
        ):
            relation_map = getattr(dto_class, relation_map_name, {}) or {}

            for dto_field_name, descriptor in relation_map.items():
                candidate_names = {dto_field_name}
                get_function_field_name = getattr(
                    descriptor,
                    "get_function_field_name",
                    None,
                )
                if callable(get_function_field_name):
                    candidate_names.add(get_function_field_name(operation))

                if field_name not in candidate_names:
                    continue

                inferred_descriptor = copy.deepcopy(descriptor)
                if operation == "update":
                    setattr(inferred_descriptor, "update_function_type", related_type)
                else:
                    setattr(inferred_descriptor, "insert_function_type", related_type)

                return (dto_field_name, inferred_descriptor)

        return None

    @classmethod
    def _infer_external_mapping(
        cls,
        function_descriptor: FunctionField,
    ) -> ty.Optional[ty.Tuple[str, ty.Any]]:
        """
        Permite que o FunctionType declare campos resolvidos fora do DTO,
        como bindings vindos de `args.<nome>` ou literais controlados.
        """
        binding_source = getattr(function_descriptor, "binding_source", None)
        if not binding_source:
            return None
        return (binding_source, function_descriptor)

    @classmethod
    def _get_lookup_operation(cls) -> ty.Optional[str]:
        operation_by_lookup = {
            "insert_function_field_lookup": "insert",
            "update_function_field_lookup": "update",
            "get_function_field_lookup": "get",
            "list_function_field_lookup": "list",
            "delete_function_field_lookup": "delete",
        }
        return operation_by_lookup.get(getattr(cls, "dto_lookup_attribute", ""))


class InsertFunctionTypeBase(FunctionTypeBase):
    dto_lookup_attribute = "insert_function_field_lookup"

    @classmethod
    def get_insert_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        return cls.get_function_mapping(dto_class)


class UpdateFunctionTypeBase(FunctionTypeBase):
    dto_lookup_attribute = "update_function_field_lookup"

    @classmethod
    def get_update_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        return cls.get_function_mapping(dto_class)


class GetFunctionTypeBase(FunctionTypeBase):
    dto_lookup_attribute = "get_function_field_lookup"

    @classmethod
    def get_get_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        return cls.get_function_mapping(dto_class)


class ListFunctionTypeBase(FunctionTypeBase):
    dto_lookup_attribute = "list_function_field_lookup"

    @classmethod
    def get_list_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        return cls.get_function_mapping(dto_class)


class DeleteFunctionTypeBase(FunctionTypeBase):
    dto_lookup_attribute = "delete_function_field_lookup"

    @classmethod
    def get_delete_function_mapping(
        cls,
        dto_class: ty.Type["DTOBase"],
    ) -> ty.Dict[str, ty.Tuple[str, ty.Any]]:
        return cls.get_function_mapping(dto_class)
