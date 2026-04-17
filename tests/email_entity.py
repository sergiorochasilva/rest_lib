import datetime

from typing import List

from rest_lib.decorator.entity import Entity
from rest_lib.entity.entity_base import EntityBase

@Entity(
    table_name="teste.email",
    pk_field="id",
    default_order_fields=["cliente_id", "email", "id"],
)
class EmailEntity(EntityBase):

    id: str = None
    cliente_id: str = None
    email: str = None
    criado_em: datetime.datetime = None
    criado_por: str = None
    atualizado_em: datetime.datetime = None
    atualizado_por: str = None
    apagado_em: datetime.datetime = None
    apagado_por: str = None
    grupo_empresarial: str = None
    tenant: int = None