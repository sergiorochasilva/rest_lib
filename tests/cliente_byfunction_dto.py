import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.descriptor.dto_list_field import DTOListField
from rest_lib.dto.dto_base import DTOBase

from tests.cliente_byfunction_endereco_dto import ClienteByfunctionEnderecoDTO
from tests.cliente_byfunction_endereco_entity import (
    ClienteByfunctionEnderecoEntity,
)
from tests.cliente_byfunction_insert_function_type import (
    ClienteByfunctionEnderecoInsertType,
)


@DTO()
class ClienteByfunctionDTO(DTOBase):

    id: uuid.UUID = DTOField(
        pk=True,
        resume=True,
        not_null=True,
        default_value=uuid.uuid4,
        validator=DTOFieldValidators().validate_uuid,
        entity_field="id",
    )
    codigo: str = DTOField(
        resume=True,
        not_null=True,
        strip=True,
        min=1,
        max=30,
        entity_field="pessoa",
    )
    nome: str = DTOField(
        resume=True,
        not_null=True,
        strip=True,
        min=1,
        max=150,
    )
    nomefantasia: str = DTOField(
        resume=True,
        not_null=True,
        strip=True,
        min=1,
        max=150,
    )
    identidade: str = DTOField(strip=True, max=20)
    documento: str = DTOField(
        resume=True,
        strip=True,
        min=11,
        max=20,
        validator=DTOFieldValidators().validate_cpf_or_cnpj,
        entity_field="cnpj",
    )
    inscricaoestadual: str = DTOField(
        resume=True,
        strip=True,
        max=20,
        entity_field="inscricaoestadual",
    )
    retemiss: bool = DTOField(default_value=False)
    retemir: bool = DTOField(default_value=False)
    retempis: bool = DTOField(default_value=False)
    retemcofins: bool = DTOField(default_value=False)
    retemcsll: bool = DTOField(default_value=False)
    reteminss: bool = DTOField(default_value=False)
    tenant: int = DTOField(
        resume=True,
        not_null=True,
        partition_data=True,
        entity_field="tenant",
    )

    enderecos: list[ClienteByfunctionEnderecoDTO] = DTOListField(
        dto_type=ClienteByfunctionEnderecoDTO,
        entity_type=ClienteByfunctionEnderecoEntity,
        related_entity_field="id_pessoa",
        relation_key_field="id",
        insert_function_field="enderecos",
        insert_function_type=ClienteByfunctionEnderecoInsertType,
    )
