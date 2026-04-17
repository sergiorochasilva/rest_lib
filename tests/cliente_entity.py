import datetime

from typing import List

from rest_lib.decorator.entity import Entity
from rest_lib.entity.entity_base import EntityBase


@Entity(
    table_name="teste.cliente",
    pk_field="id",
    default_order_fields=["estabelecimento", "cliente", "id"],
)
class ClienteEntity(EntityBase):

    # Atributos do relacionamento
    id: str = None
    estabelecimento: str = None
    cliente: str = None
    # Atributos de auditoria
    criado_em: datetime.datetime = None
    criado_por: str = None
    atualizado_em: datetime.datetime = None
    atualizado_por: str = None
    apagado_em: datetime.datetime = None
    apagado_por: str = None
    # Atributos de segmentação dos dados
    grupo_empresarial: str = None
    tenant: int = None
