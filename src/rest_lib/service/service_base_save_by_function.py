import datetime
import typing as ty
import uuid

from flask import has_request_context, request

from rest_lib.descriptor.dto_list_field import DTOListField
from rest_lib.descriptor.dto_object_field import DTOObjectField
from rest_lib.descriptor.dto_one_to_one_field import DTOOneToOneField
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.function_type_base import (
    FunctionTypeBase,
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)
from rest_lib.util.enum_util import coerce_enum_value


class ServiceBaseSaveByFunction:
    _insert_function_type_class: ty.Optional[ty.Type[InsertFunctionTypeBase]] = None
    _update_function_type_class: ty.Optional[ty.Type[UpdateFunctionTypeBase]] = None

    def set_insert_function_type_class(
        self,
        insert_function_type_class: ty.Optional[
            ty.Type[InsertFunctionTypeBase]
        ],
    ):
        if insert_function_type_class is not None and not issubclass(
            insert_function_type_class, InsertFunctionTypeBase
        ):
            raise ValueError(
                "A classe informada em insert_function_type_class deve herdar de InsertFunctionTypeBase."
            )

        self._insert_function_type_class = insert_function_type_class

        if (
            self._insert_function_type_class is not None
            and getattr(self, "_dto_class", None) is not None
        ):
            self._insert_function_type_class.get_function_mapping(
                self._dto_class)

    def set_update_function_type_class(
        self,
        update_function_type_class: ty.Optional[
            ty.Type[UpdateFunctionTypeBase]
        ],
    ):
        if update_function_type_class is not None and not issubclass(
            update_function_type_class, UpdateFunctionTypeBase
        ):
            raise ValueError(
                "A classe informada em update_function_type_class deve herdar de UpdateFunctionTypeBase."
            )

        self._update_function_type_class = update_function_type_class

        if (
            self._update_function_type_class is not None
            and getattr(self, "_dto_class", None) is not None
        ):
            self._update_function_type_class.get_function_mapping(
                self._dto_class)

    def _build_insert_function_type_object(
        self,
        dto: DTOBase,
        insert_function_type_class: ty.Optional[
            ty.Type[InsertFunctionTypeBase]
        ] = None,
    ):
        return self._build_function_type_object(
            dto,
            insert_function_type_class,
            self._insert_function_type_class,
            operation="insert",
        )

    def _build_update_function_type_object(
        self,
        dto: DTOBase,
        update_function_type_class: ty.Optional[
            ty.Type[UpdateFunctionTypeBase]
        ] = None,
    ):
        return self._build_function_type_object(
            dto,
            update_function_type_class,
            self._update_function_type_class,
            operation="update",
        )

    def _build_function_type_object(
        self,
        dto: DTOBase,
        override_class: ty.Optional[ty.Type[FunctionTypeBase]],
        default_class: ty.Optional[ty.Type[FunctionTypeBase]],
        operation: str,
    ):
        target_class = override_class or default_class

        if target_class is None:
            return None

        mapping_dto_class = (
            dto.__class__ if override_class is not None else self._dto_class
        )

        mapping = target_class.get_function_mapping(mapping_dto_class)

        return self._build_function_type_object_from_mapping(
            dto,
            target_class,
            mapping,
            operation=operation,
        )

    def _build_function_type_object_from_mapping(
        self,
        dto: DTOBase,
        function_type_class: ty.Type[FunctionTypeBase],
        mapping: ty.Dict[str, ty.Tuple[str, ty.Any]],
        operation: str,
    ) -> FunctionTypeBase:
        if mapping is None:
            raise ValueError(
                f"FunctionType '{function_type_class.__name__}' não possui mapeamentos configurados."
            )

        insert_object = function_type_class()
        for function_field_name, (dto_field_name, descriptor) in mapping.items():
            if self._is_external_binding_source(dto_field_name):
                field_exists, field_value, field_owner = (
                    self._resolve_external_binding_value(
                        dto,
                        dto_field_name,
                        descriptor,
                    )
                )
            else:
                field_exists, field_value, field_owner = self._resolve_dto_field_value(
                    dto,
                    dto_field_name,
                )

            if not field_exists:
                raise ValueError(
                    f"DTO '{dto.__class__.__name__}' não possui o campo '{dto_field_name}' utilizado em '{function_type_class.__name__}'."
                )

            value = coerce_enum_value(field_value)
            dto_values = getattr(field_owner, "__dict__", dto.__dict__)

            convert_to_function = getattr(
                descriptor, "convert_to_function", None)
            if convert_to_function is not None:
                converted_values = convert_to_function(value, dto_values) or {}

                if not isinstance(converted_values, dict):
                    raise ValueError(
                        f"A função 'convert_to_function' configurada no campo '{dto_field_name}' deve retornar um dicionário."
                    )

                if function_field_name not in converted_values:
                    converted_values = {
                        function_field_name: None,
                        **converted_values,
                    }

                for target_field, target_value in converted_values.items():
                    setattr(insert_object, target_field, target_value)
                continue

            if isinstance(
                descriptor,
                (DTOListField, DTOObjectField, DTOOneToOneField),
            ):
                relation_value = self._build_function_relation_value(
                    descriptor,
                    value,
                    operation,
                )
                if relation_value is not None:
                    setattr(insert_object, function_field_name, relation_value)
                continue

            setattr(insert_object, function_field_name, value)

        return insert_object

    def _is_external_binding_source(self, binding_source: ty.Any) -> bool:
        """
        Identifica bindings que não devem ser lidos do DTO durante a montagem
        do payload da função.
        """
        return isinstance(binding_source, str) and (
            binding_source.startswith("args.") or binding_source == "literal:null"
        )

    def _resolve_dto_field_value(
        self,
        dto: DTOBase,
        dto_field_name: str,
    ) -> tuple[bool, ty.Any, ty.Any]:
        """
        Resolves a DTO value, supporting dotted paths produced by FunctionType
        mappings for aggregator fields (for example
        `situacao_fiscal.indicador_inscricao_estadual`).

        Returns a tuple `(field_exists, field_value, field_owner)` so callers
        can keep using the descriptor owner's `__dict__` when invoking
        `convert_to_function`.
        """
        field_path = dto_field_name.split(".")
        current_value: ty.Any = dto
        current_owner: ty.Any = dto

        for index, field_name in enumerate(field_path):
            if current_value is None:
                return True, None, current_owner

            if not hasattr(current_value, field_name):
                return False, None, current_value

            current_owner = current_value
            current_value = getattr(current_value, field_name, None)

            if current_value is None and index < len(field_path) - 1:
                return True, None, current_owner

        return True, current_value, current_owner

    def _resolve_external_binding_value(
        self,
        dto: DTOBase,
        binding_source: str,
        descriptor: ty.Any,
    ) -> tuple[bool, ty.Any, ty.Any]:
        """
        Resolve bindings declarados fora do DTO.

        No momento suportamos `args.<nome>`, usado por handlers insert/update
        que dependem de parâmetros vindos da query string.
        """
        if not has_request_context():
            if binding_source == "literal:null":
                return True, None, dto
            raise ValueError(
                f"O binding externo '{binding_source}' requer um contexto HTTP ativo."
            )

        if binding_source == "literal:null":
            return True, None, dto

        if binding_source.startswith("args."):
            arg_name = binding_source[5:]
            raw_value = request.args.get(arg_name)
            return True, self._coerce_external_binding_value(raw_value, descriptor), dto

        raise ValueError(f"Binding externo '{binding_source}' não é suportado.")

    def _coerce_external_binding_value(
        self,
        raw_value: ty.Any,
        descriptor: ty.Any,
    ) -> ty.Any:
        """
        Converte valores vindos de bindings externos usando o tipo esperado pelo
        descriptor do FunctionType, preservando o mesmo contrato usado pelos
        campos mapeados a partir do DTO.
        """
        if raw_value is None:
            return None

        expected_type = getattr(descriptor, "expected_type", None)
        if expected_type is None:
            return raw_value

        origin = ty.get_origin(expected_type)
        args = ty.get_args(expected_type)
        if origin is ty.Union:
            non_none_args = [arg for arg in args if arg is not type(None)]  # noqa: E721
            if len(non_none_args) == 1:
                expected_type = non_none_args[0]

        if expected_type is uuid.UUID:
            return uuid.UUID(str(raw_value))
        if expected_type is int:
            return int(raw_value)
        if expected_type is float:
            return float(raw_value)
        if expected_type is bool:
            normalized = str(raw_value).strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
            return raw_value
        if expected_type is datetime.date:
            return datetime.date.fromisoformat(str(raw_value))
        if expected_type is datetime.datetime:
            return datetime.datetime.fromisoformat(str(raw_value))
        if expected_type is datetime.time:
            return datetime.time.fromisoformat(str(raw_value))

        return raw_value

    def _build_function_relation_value(
        self,
        descriptor: ty.Union[DTOListField, DTOObjectField, DTOOneToOneField],
        value: ty.Any,
        operation: str,
    ):
        if value is None:
            return None

        function_type_class = descriptor.get_function_type(operation)
        if function_type_class is None:
            raise ValueError(
                f"O campo '{descriptor.name}' precisa informar 'function_type' para relacionamentos ({operation})."
            )

        dto_class = self._get_relation_dto_class(descriptor)
        mapping = function_type_class.get_function_mapping(dto_class)

        if isinstance(descriptor, DTOListField):
            related_values = []
            for item in value:
                dto_instance = self._ensure_dto_instance(item, dto_class)
                if dto_instance is None:
                    continue
                related_values.append(
                    self._build_function_type_object_from_mapping(
                        dto_instance,
                        function_type_class,
                        mapping,
                        operation=operation,
                    )
                )
            return related_values

        dto_instance = self._ensure_dto_instance(value, dto_class)
        if dto_instance is None:
            return None

        return self._build_function_type_object_from_mapping(
            dto_instance,
            function_type_class,
            mapping,
            operation=operation,
        )

    def _get_relation_dto_class(
        self, descriptor: ty.Union[DTOListField, DTOObjectField, DTOOneToOneField]
    ) -> ty.Type[DTOBase]:
        if isinstance(descriptor, DTOListField):
            return descriptor.dto_type
        return descriptor.expected_type

    def _ensure_dto_instance(
        self,
        value: ty.Any,
        dto_class: ty.Type[DTOBase],
    ) -> ty.Optional[DTOBase]:
        if value is None:
            return None

        if isinstance(value, dto_class):
            return value

        if isinstance(value, dict):
            return dto_class(**value)

        raise ValueError(
            f"O valor informado para o relacionamento deveria ser do tipo '{dto_class.__name__}'. Valor recebido: {type(value)}."
        )
