import enum

from rest_lib.util.enum_util import coerce_enum_value, enum_to_primitive_value


class TupleEnum(enum.Enum):
    A = ("A", 10, 99)

    def get_entity_index(self):
        return 2


class TupleEnumDefault(enum.Enum):
    A = ("A", 10, 99)


class PlainEnum(enum.Enum):
    A = 7


def test_enum_to_primitive_value_uses_get_entity_index():
    assert enum_to_primitive_value(TupleEnum.A) == 99


def test_enum_to_primitive_value_default_index():
    assert enum_to_primitive_value(TupleEnumDefault.A) == 10


def test_enum_to_primitive_value_plain_enum():
    assert enum_to_primitive_value(PlainEnum.A) == 7


def test_coerce_enum_value_passthrough():
    assert coerce_enum_value("valor") == "valor"
