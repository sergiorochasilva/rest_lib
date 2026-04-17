import uuid

from rest_lib.decorator.entity import Entity
from rest_lib.descriptor.entity_field import EntityField
from rest_lib.entity.entity_base import EntityBase


@Entity(
    table_name="teste.enderecos",
    pk_field="endereco",
    default_order_fields=["logradouro", "numero"],
)
class ClienteByfunctionEnderecoEntity(EntityBase):

    endereco: uuid.UUID = EntityField()
    tipologradouro: str = EntityField()
    logradouro: str = EntityField()
    numero: str = EntityField()
    complemento: str = EntityField()
    cep: str = EntityField()
    bairro: str = EntityField()
    tipoendereco: int = EntityField()
    enderecopadrao: int = EntityField()
    referencia: str = EntityField()
    uf: str = EntityField()
    cidade: str = EntityField()
    pais: str = EntityField()
    id_pessoa: uuid.UUID = EntityField()
    tenant: int = EntityField()
