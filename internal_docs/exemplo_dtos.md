# Exemplos de Construção de DTOs

Abaixo, seguem exemplos de construção de DTOs do Rest Lib, a partir de diversas especificações de tabelas:

## Exemplo 1 - Tabela Telefone

### Tabela de origem:
```sql
CREATE TABLE ns.telefones (
	ddd varchar(3) NULL,
	telefone varchar(20) NULL,
	chavetel varchar(20) NULL,
	descricao varchar(100) NULL,
	ramal varchar(12) NULL,
	tptelefone int4 NULL,
	lastupdate timestamp NULL DEFAULT now(),
	ddi varchar(3) NULL,
	ordemimportancia int2 NULL,
	contato uuid NULL,
	id_pessoa uuid NULL,
	id uuid NOT NULL DEFAULT uuid_generate_v4(),
	principal bool NOT NULL DEFAULT false,
	tenant int8 NULL,
	id_pessoafisica uuid NULL,
	CONSTRAINT "PK_telefones_id" PRIMARY KEY (id),
	CONSTRAINT "FK_ns.telefones_contato" FOREIGN KEY (contato) REFERENCES ns.contatos(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT "FK_ns.telefones_id_pessoa" FOREIGN KEY (id_pessoa) REFERENCES ns.pessoas(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT "FK_telefones_pessoasfisicas" FOREIGN KEY (id_pessoafisica) REFERENCES ns.pessoasfisicas(pessoafisica) ON DELETE CASCADE DEFERRABLE
);
```

### DTO Gerado:
```python
import datetime
import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.dto.dto_base import DTOBase

from nasajon.enumerators.tipo_telefone_erp3 import TipoTelefoneERP3


@DTO()
class TelefoneERP3DTO(DTOBase):
    # Atributos da entidade
    id: uuid.UUID = DTOField(
        resume=True,
        pk=True,
        not_null=True,
        default_value=uuid.uuid4,
        strip=True,
        min=36,
        max=36,
        validator=DTOFieldValidators().validate_uuid,
    )
    ddd: str = DTOField(resume=True, not_null=True, strip=True, min=1, max=3)
    telefone: str = DTOField(resume=True, not_null=True, strip=True, min=1, max=20)
    chave: str = DTOField(strip=True, min=1, max=20, entity_field="chavetel")
    descricao: str = DTOField(resume=True, strip=True, min=1, max=100)
    ramal: str = DTOField(strip=True, min=1, max=12)
    tipo: TipoTelefoneERP3 = DTOField(resume=True, not_null=True, entity_field="tptelefone")
    ddi: str = DTOField(strip=True, min=1, max=3)
    ordem: int = DTOField(min=0, max=32767, entity_field="ordemimportancia")
    # contato: uuid.UUID = DTOField()
    id_pessoa: uuid.UUID = DTOField()
    principal: bool = DTOField(resume=True, not_null=True, default_value=False)

    # Atributos de auditoria
    atualizado_em: datetime.datetime = DTOField(
        resume=True,
        not_null=True,
        default_value=datetime.datetime.now,
        entity_field="lastupdate",
    )
```

## Exemplo 2 - Tabela Grupo Empresarial

### Tabela de origem:
```sql
CREATE TABLE ns.gruposempresariais (
	codigo varchar(30) NOT NULL,
	descricao varchar(150) NULL,
	usagrade int2 NULL,
	grupoempresarial uuid NOT NULL DEFAULT uuid_generate_v4(),
	lastupdate timestamp NULL DEFAULT now(),
	modogestaopatrimonial bool NOT NULL DEFAULT false,
	escopoworkflow int8 NULL,
	id_erp int8 NULL,
	modocomissoes int4 NULL,
	modo_calculo_pmc int4 NOT NULL DEFAULT 0,
	importacao_hash varchar NULL,
	tenant int8 NULL DEFAULT 0,
	inativo bool NULL,
	CONSTRAINT "PK_gruposempresariais_grupoempresarial" PRIMARY KEY (grupoempresarial),
	CONSTRAINT "UK_ns.gruposempresariais_codigo_mgp" UNIQUE (codigo, modogestaopatrimonial),
	CONSTRAINT "FK_ns.gruposempresariais.escopoworkflow" FOREIGN KEY (escopoworkflow) REFERENCES workflow.escopo(escopoworkflow)
);
```

### DTO Gerado:
```python
import datetime
import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField, DTOFieldFilter
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.descriptor.filter_operator import FilterOperator
from rest_lib.dto.dto_base import DTOBase


@DTO()
class GrupoEmpresarialERP3DTO(DTOBase):
    # Atributos gerais
    pk: uuid.UUID = DTOField(
        resume=True,
        pk=True,
        not_null=True,
        strip=True,
        min=1,
        max=36,
        validator=DTOFieldValidators().validate_uuid,
        default_value=uuid.uuid4,
        entity_field="grupoempresarial",
    )
    id: str = DTOField(
        resume=True,
        not_null=True,
        strip=True,
        min=1,
        max=30,
        candidate_key=True,
        unique="codigo",
    )
    descricao: str = DTOField(
        resume=True,
        not_null=True,
        strip=True,
        min=1,
        max=250,
    )
    escopo_workflow: int = DTOField(
        resume=True,
        not_null=True,
        entity_field="escopoworkflow",
    )
    # Atributos de auditoria
    atualizado_em: datetime.datetime = DTOField(
        resume=True,
        filters=[
            DTOFieldFilter("atualizado_apos", FilterOperator.GREATER_THAN),
            DTOFieldFilter("atualizado_antes", FilterOperator.LESS_THAN),
        ],
        default_value=datetime.datetime.now,
        entity_field="lastupdate",
    )
```

## Exemplo 3 - Tabela Email

### Tabela de origem:
```sql
CREATE TABLE `email` (
  `id` varchar(36) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `email` varchar(150) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `participante` varchar(30) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `descricao` varchar(150) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `principal` tinyint(1) DEFAULT NULL,
  `pessoal` tinyint(1) DEFAULT NULL,
  `financeiro` tinyint(1) DEFAULT NULL,
  `faturamento` tinyint(1) DEFAULT NULL,
  `comercial` tinyint(1) DEFAULT NULL,
  `ordem` smallint(6) DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `criado_por` varchar(150) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `atualizado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_por` varchar(150) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `apagado_em` datetime DEFAULT NULL,
  `apagado_por` varchar(150) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `grupo_empresarial` varchar(36) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `tenant` bigint(20) NOT NULL,
  UNIQUE KEY `PRIMARY` (`tenant`,`grupo_empresarial`,`id`) USING HASH,
  SHARD KEY `__SHARDKEY` (`tenant`,`grupo_empresarial`,`id`),
  SORT KEY `__UNORDERED` ()
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES';
```

### DTO Gerado:
```python
import datetime
import uuid

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_field_validators import DTOFieldValidators
from rest_lib.dto.dto_base import DTOBase


@DTO()
class EmailDTO(DTOBase):

    # Atributos da entidade
    id: uuid.UUID = DTOField(pk=True, resume=True, not_null=True,
                             validator=DTOFieldValidators().validate_uuid, default_value=uuid.uuid4)
    email: str = DTOField(resume=True, not_null=True, strip=True,
                          min=1, max=150, validator=DTOFieldValidators().validate_email)
    descricao: str = DTOField(resume=True, strip=True, min=1, max=150)
    principal: bool = DTOField(resume=True)
    pessoal: bool = DTOField()
    financeiro: bool = DTOField()
    faturamento: bool = DTOField()
    comercial: bool = DTOField()
    ordem: int = DTOField(max=255)
    # Atributos de auditoria
    criado_em: datetime.datetime = DTOField(
        resume=True, not_null=True, default_value=datetime.datetime.now)
    criado_por: str = DTOField(resume=True, not_null=False, strip=True,
                               min=1, max=150, validator=DTOFieldValidators().validate_email)
    atualizado_em: datetime.datetime = DTOField(
        resume=True, not_null=True, default_value=datetime.datetime.now)
    atualizado_por: str = DTOField(resume=True, not_null=False, strip=True,
                                   min=1, max=150, validator=DTOFieldValidators().validate_email)
    apagado_em: datetime.datetime = DTOField()
    apagado_por: str = DTOField(
        strip=True, min=1, max=150, validator=DTOFieldValidators().validate_email)
    # Atributos de segmentação dos dados
    grupo_empresarial: uuid.UUID = DTOField(
        resume=True, not_null=True, partition_data=True)
    tenant: int = DTOField(resume=True, not_null=True, partition_data=True)
```