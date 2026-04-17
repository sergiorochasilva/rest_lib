import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.dto.dto_base import DTOBase


@DTO(fixed_filters={"cliente_ativado": 1, "inativo": 0})
class BaseClienteDTO(DTOBase):
    id: uuid.UUID = DTOField(
        pk=True,
        not_null=True,
        validator=DTOFieldValidators().validate_uuid,
        default_value=uuid.uuid4,
    )

    cliente_ativado: int = DTOField(not_null=True)
    inativo: int = DTOField(not_null=True)


@DTO(partial_of={"dto": BaseClienteDTO, "relation_field": "id_pessoa"})
class PartialContratanteDTO(DTOBase):
    id: uuid.UUID = DTOField(
        pk=True,
        not_null=True,
        validator=DTOFieldValidators().validate_uuid,
        default_value=uuid.uuid4,
    )

    foto: str = DTOField()


@DTO(
    fixed_filters={"inativo": 1},
    partial_of={"dto": BaseClienteDTO, "relation_field": "id_pessoa"},
)
class PartialContratanteOverrideDTO(DTOBase):
    id: uuid.UUID = DTOField(
        pk=True,
        not_null=True,
        validator=DTOFieldValidators().validate_uuid,
        default_value=uuid.uuid4,
    )

    foto: str = DTOField()


def test_partial_of_inherits_parent_fixed_filters_when_missing() -> None:
    assert PartialContratanteDTO.fixed_filters == {"cliente_ativado": 1, "inativo": 0}


def test_partial_of_merges_parent_fixed_filters_with_child_override() -> None:
    assert PartialContratanteOverrideDTO.fixed_filters == {
        "cliente_ativado": 1,
        "inativo": 1,
    }

