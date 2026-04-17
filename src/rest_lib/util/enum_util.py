import enum
import typing as ty


def enum_to_primitive_value(value: enum.Enum) -> ty.Any:
    """
    Converte um Enum em um valor primitivo, respeitando get_entity_index() quando
    o valor do Enum for uma tupla/lista.
    """
    raw = value.value
    if isinstance(raw, (list, tuple)):
        get_index = getattr(value, "get_entity_index", None)
        tuple_index = get_index() if callable(get_index) else 1
        return raw[tuple_index]
    return raw


def coerce_enum_value(value: ty.Any) -> ty.Any:
    if isinstance(value, enum.Enum):
        return enum_to_primitive_value(value)
    return value
