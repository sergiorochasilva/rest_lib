import uuid

from rest_lib.decorator.entity import Entity
from rest_lib.descriptor.entity_field import EntityField
from rest_lib.entity.entity_base import EntityBase


@Entity(
    table_name="teste.pessoas",
    pk_field="id",
    default_order_fields=["pessoa"],
)
class ClienteByfunctionEntity(EntityBase):

    id: uuid.UUID = EntityField()
    pessoa: str = EntityField()
    nome: str = EntityField()
    nomefantasia: str = EntityField()
    identidade: str = EntityField()
    cnpj: str = EntityField()
    inscricaoestadual: str = EntityField()
    tenant: int = EntityField()
