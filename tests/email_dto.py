import datetime
import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField, DTOFieldFilter
from rest_lib.descriptor.dto_list_field import DTOListField
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.dto.dto_base import DTOBase


@DTO()
class EmailDTO(DTOBase):

    # Atributos do relacionamento
    id: uuid.UUID = DTOField(resume=True, pk=True, not_null=True,
                             validator=DTOFieldValidators().validate_uuid, default_value=uuid.uuid4)
    cliente_id: str = DTOField(
        resume=True, not_null=True,validator=DTOFieldValidators().validate_uuid, default_value=uuid.uuid4)
    email: str = DTOField(resume=True, not_null=True, strip=True)
    # Atributos de auditoria
    criado_em: datetime.datetime = DTOField(
        resume=True,
        filters=[
            DTOFieldFilter('criado_apos', FilterOperator.GREATER_THAN),
            DTOFieldFilter('criado_antes', FilterOperator.LESS_THAN),
        ],
        default_value=datetime.datetime.now
    )
    criado_por: str = DTOField(
        resume=True, not_null=False, strip=True, min=1, max=150, validator=DTOFieldValidators().validate_email)
    atualizado_em: datetime.datetime = DTOField(
        resume=True,
        filters=[
            DTOFieldFilter('atualizado_apos', FilterOperator.GREATER_THAN),
            DTOFieldFilter('atualizado_antes', FilterOperator.LESS_THAN),
        ],
        default_value=datetime.datetime.now
    )
    atualizado_por: str = DTOField(
        resume=True, not_null=False, strip=True, min=1, max=150, validator=DTOFieldValidators().validate_email)
    apagado_em: datetime.datetime = DTOField(
        filters=[
            DTOFieldFilter('apagado_apos', FilterOperator.GREATER_THAN),
            DTOFieldFilter('apagado_antes', FilterOperator.LESS_THAN),
        ]
    )
    apagado_por: str = DTOField(
        strip=True, min=1, max=150, validator=DTOFieldValidators().validate_email)
    # Atributos de segmentação dos dados
    grupo_empresarial: uuid.UUID = DTOField(
        resume=True, not_null=True, partition_data=True)
    tenant: int = DTOField(resume=True, not_null=True, partition_data=True)
