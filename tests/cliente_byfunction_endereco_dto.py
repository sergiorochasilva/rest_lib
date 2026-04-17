import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.dto.dto_base import DTOBase


@DTO()
class ClienteByfunctionEnderecoDTO(DTOBase):

    endereco: uuid.UUID = DTOField(
        pk=True,
        resume=True,
        not_null=True,
        default_value=uuid.uuid4,
        entity_field="endereco",
    )
    tipologradouro: str = DTOField(strip=True, min=1, max=10)
    logradouro: str = DTOField(strip=True, min=1, max=150)
    numero: str = DTOField(strip=True, min=1, max=10)
    complemento: str = DTOField(strip=True, max=60)
    cep: str = DTOField(strip=True, min=1, max=15)
    bairro: str = DTOField(strip=True, min=1, max=60)
    tipo: int = DTOField(entity_field="tipoendereco")
    enderecopadrao: int = DTOField()
    referencia: str = DTOField(strip=True, max=150)
    uf: str = DTOField(strip=True, min=2, max=2)
    cidade: str = DTOField(strip=True, max=60)
    tenant: int = DTOField(partition_data=True, entity_field="tenant")
