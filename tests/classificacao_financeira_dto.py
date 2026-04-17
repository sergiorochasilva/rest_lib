import datetime
import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField, DTOFieldFilter
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.dto.dto_base import DTOBase


@DTO()
class ClassificacaoFinanceiraDTO(DTOBase):

    id: uuid.UUID = DTOField(
        pk=True,
        resume=True,
        not_null=True,
        default_value=uuid.uuid4,
        strip=True,
        min=36,
        max=36,
        validator=DTOFieldValidators().validate_uuid,
        entity_field="classificacaofinanceira",
        update_function_field="classificacao",
        get_function_field="classificacao",
    )

    codigo: str = DTOField(resume=True, not_null=True, strip=True, min=1, max=30)
    descricao: str = DTOField(
        resume=True,
        strip=True,
        min=1,
        max=150,
        insert_function_field="descricao_func",
        update_function_field="descricao",
        get_function_field="descricao_func",
    )
    codigocontabil: str = DTOField(strip=True, min=1, max=20)
    resumo: str = DTOField(strip=True, min=1, max=30)
    situacao: int = DTOField(not_null=True, default_value=0)
    versao: int = DTOField(default_value=1)
    natureza: int = DTOField(default_value=0)
    paiid: uuid.UUID = DTOField(update_function_field="classificacaopai")
    grupoempresarial: uuid.UUID = DTOField(resume=True)
    resumoexplicativo: str = DTOField()
    importacao_hash: str = DTOField()
    iniciogrupo: bool = DTOField(default_value=False)
    apenasagrupador: bool = DTOField(default_value=False)
    id_erp: int = DTOField()
    padrao: bool = DTOField(default_value=False)
    transferencia: bool = DTOField(default_value=False)
    repasse_deducao: bool = DTOField(default_value=False)
    tenant: int = DTOField()
    rendimentos: bool = DTOField(default_value=False)
    categoriafinanceira: uuid.UUID = DTOField()
    grupobalancete: str = DTOField(strip=True, min=1, max=150)
    atributo1: str = DTOField(strip=True, min=1, max=50)
    atributo2: str = DTOField(strip=True, min=1, max=50)
    atributo3: str = DTOField(strip=True, min=1, max=50)

    # Auditoria
    atualizado_em: datetime.datetime = DTOField(
        filters=[
            DTOFieldFilter("atualizado_apos", FilterOperator.GREATER_THAN),
            DTOFieldFilter("atualizado_antes", FilterOperator.LESS_THAN),
        ],
        default_value=datetime.datetime.now,
        entity_field="lastupdate",
    )
