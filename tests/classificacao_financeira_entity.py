import datetime
import uuid

from rest_lib.entity.entity_base import EntityBase
from rest_lib.decorator.entity import Entity
from rest_lib.descriptor.entity_field import EntityField


@Entity(
    table_name="teste.classificacoesfinanceiras",
    pk_field="classificacaofinanceira",
    default_order_fields=["codigo"],
)
class ClassificacaoFinanceiraEntity(EntityBase):

    classificacaofinanceira: uuid.UUID = EntityField()
    codigo: str = EntityField()
    descricao: str = EntityField()
    codigocontabil: str = EntityField()
    resumo: str = EntityField()
    situacao: int = None
    versao: int = None
    natureza: int = EntityField()
    paiid: uuid.UUID = EntityField()
    grupoempresarial: uuid.UUID = EntityField()
    lastupdate: datetime.datetime = None
    resumoexplicativo: str = None
    importacao_hash: str = None
    iniciogrupo: bool = None
    apenasagrupador: bool = None
    id_erp: int = None
    padrao: bool = None
    transferencia: bool = EntityField()
    repasse_deducao: bool = EntityField()
    tenant: int = None
    rendimentos: bool = EntityField()
    categoriafinanceira: uuid.UUID = None
    grupobalancete: str = None
    atributo1: str = None
    atributo2: str = None
    atributo3: str = None
