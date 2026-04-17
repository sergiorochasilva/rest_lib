import enum
import uuid

from flask import Flask
from rest_lib.dao.dao_base_save_by_function import DAOBaseSaveByFunction
from rest_lib.decorator.dto import DTO
from rest_lib.decorator.entity import Entity
from rest_lib.decorator.insert_function_type import InsertFunctionType
from rest_lib.decorator.update_function_type import UpdateFunctionType
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_list_field import DTOListField
from rest_lib.descriptor.dto_one_to_one_field import (
    DTOOneToOneField,
    OTORelationType,
)
from rest_lib.descriptor.function_relation_field import FunctionRelationField
from rest_lib.descriptor.entity_field import EntityField
from rest_lib.descriptor.function_field import FunctionField
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)
from rest_lib.service.service_base import ServiceBase


@DTO()
class DummyDTO(DTOBase):
    valor: int = DTOField(
        insert_function_field="valor_func",
        update_function_field="valor_update",
    )

    descricao: str = DTOField(
        insert_function_field="descricao_func",
        convert_to_function=lambda value, dto_values: {
            "descricao_func": value.upper() if value else value,
            "valor_func": (dto_values.get("valor") or 0) + 10,
            "valor_update": (dto_values.get("valor") or 0) + 10,
        },
    )


@Entity(table_name="teste.dummy", pk_field="id", default_order_fields=["id"])
class DummyEntity(EntityBase):
    id: int = EntityField()
    valor: int = EntityField()


@InsertFunctionType(type_name="teste.tdummy")
class DummyInsertType(InsertFunctionTypeBase):
    valor_func: int = FunctionField()
    descricao_func: str = FunctionField()


class StatusEnum(enum.Enum):
    ACTIVE = ("A", 1, 99)

    def get_entity_index(self):
        return 2


@DTO()
class EnumDTO(DTOBase):
    status: StatusEnum = DTOField(insert_function_field="status_func")


@InsertFunctionType(type_name="teste.tenum")
class EnumInsertType(InsertFunctionTypeBase):
    status_func: int = FunctionField()


@InsertFunctionType(type_name="teste.tendereco")
class AddressInsertType(InsertFunctionTypeBase):
    rua: str = FunctionField()
    numero: str = FunctionField()


@InsertFunctionType(type_name="teste.tendereco_alias")
class AddressAliasInsertType(InsertFunctionTypeBase):
    tipologradouro: str = FunctionField()
    enderecopadrao: str = FunctionField()


@InsertFunctionType(type_name="teste.tdocumento")
class DocumentInsertType(InsertFunctionTypeBase):
    numero: str = FunctionField()
    tipo: str = FunctionField()


@InsertFunctionType(
    type_name="teste.tcliente_relacionado",
)
class CustomerWithRelationsInsertType(InsertFunctionTypeBase):
    nome: str = FunctionField()
    enderecos: list[AddressInsertType] = FunctionRelationField()
    documento: DocumentInsertType = FunctionRelationField()


@UpdateFunctionType(type_name="teste.tdummy_upd")
class DummyUpdateType(UpdateFunctionTypeBase):
    valor_update: int = FunctionField()
    descricao_func: str = FunctionField()


@UpdateFunctionType(
    type_name="teste.tendereco_upd"
)
class AddressUpdateType(UpdateFunctionTypeBase):
    rua: str = FunctionField()
    numero: str = FunctionField()


@UpdateFunctionType(
    type_name="teste.tdocumento_upd"
)
class DocumentUpdateType(UpdateFunctionTypeBase):
    numero: str = FunctionField()
    tipo: str = FunctionField()


@UpdateFunctionType(
    type_name="teste.tcliente_relacionado_upd",
)
class CustomerWithRelationsUpdateType(UpdateFunctionTypeBase):
    nome: str = FunctionField()
    enderecos_update: list[AddressUpdateType] = FunctionRelationField()
    documento_update: DocumentUpdateType = FunctionRelationField()


@InsertFunctionType(type_name="teste.tendereco_null")
class AddressInsertWithNullType(InsertFunctionTypeBase):
    idpessoa: uuid.UUID = FunctionField(binding_source="literal:null")
    rua: str = FunctionField()


@InsertFunctionType(type_name="teste.tcliente_relacionado_null")
class CustomerWithNullRelationInsertType(InsertFunctionTypeBase):
    nome: str = FunctionField()
    enderecos: list[AddressInsertWithNullType] = FunctionRelationField()


@InsertFunctionType(type_name="teste.tcliente_relacionado_alias")
class CustomerWithEntityFieldAliasInsertType(InsertFunctionTypeBase):
    nome: str = FunctionField()
    enderecos: list[AddressAliasInsertType] = FunctionRelationField()


@DTO()
class AddressDTO(DTOBase):
    rua: str = DTOField()
    numero: str = DTOField()


@DTO()
class AddressAliasDTO(DTOBase):
    tipo_logradouro: str = DTOField(entity_field="tipologradouro")
    padrao: str = DTOField(entity_field="enderecopadrao")


@DTO()
class DocumentDTO(DTOBase):
    numero: str = DTOField(pk=True)
    tipo: str = DTOField()


@DTO()
class CustomerWithRelationsDTO(DTOBase):
    id: int = DTOField(pk=True)
    nome: str = DTOField()

    enderecos: list[AddressDTO] = DTOListField(
        dto_type=AddressDTO,
        entity_type=DummyEntity,
        related_entity_field="cliente_id",
        relation_key_field="id",
        insert_function_field="enderecos",
        insert_function_type=AddressInsertType,
        update_function_field="enderecos_update",
        update_function_type=AddressUpdateType,
    )

    documento: DocumentDTO = DTOOneToOneField(
        entity_type=DummyEntity,
        relation_type=OTORelationType.COMPOSITION,
        insert_function_field="documento",
        insert_function_type=DocumentInsertType,
        update_function_field="documento_update",
        update_function_type=DocumentUpdateType,
    )


@DTO()
class CustomerWithEntityFieldAliasDTO(DTOBase):
    id: int = DTOField(pk=True)
    nome: str = DTOField()

    enderecos: list[AddressAliasDTO] = DTOListField(
        dto_type=AddressAliasDTO,
        entity_type=DummyEntity,
        related_entity_field="cliente_id",
        relation_key_field="id",
        insert_function_field="enderecos",
        insert_function_type=AddressAliasInsertType,
    )


class DummyDAO:
    _db = None


class FakeInjector:
    def db_adapter(self):
        return None


def test_build_insert_function_type_object_with_mapped_fields():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        DummyDTO,
        DummyEntity,
        insert_function_type_class=DummyInsertType,
        insert_function_name="teste.fn_dummy",
    )

    dto = DummyDTO()
    dto.valor = 2
    dto.descricao = "nova descricao"

    insert_object = service._build_insert_function_type_object(dto)

    assert insert_object.valor_func == 12
    assert insert_object.descricao_func == "NOVA DESCRICAO"


def test_build_insert_function_type_object_with_enum_value():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        EnumDTO,
        DummyEntity,
        insert_function_type_class=EnumInsertType,
        insert_function_name="teste.fn_enum",
    )

    dto = EnumDTO()
    dto.status = StatusEnum.ACTIVE

    insert_object = service._build_insert_function_type_object(dto)

    assert insert_object.status_func == 99


def test_build_insert_function_type_object_with_relations():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        CustomerWithRelationsDTO,
        DummyEntity,
        insert_function_type_class=CustomerWithRelationsInsertType,
        insert_function_name="teste.fn_cliente_relacionado",
    )

    dto = CustomerWithRelationsDTO()
    dto.nome = "Cliente Teste"

    addr1 = AddressDTO()
    addr1.rua = "Rua A"
    addr1.numero = "10"

    addr2 = AddressDTO()
    addr2.rua = "Rua B"
    addr2.numero = "20"

    dto.enderecos = [addr1, addr2]

    document = DocumentDTO()
    document.numero = "123"
    document.tipo = "CPF"
    dto.documento = document

    insert_object = service._build_insert_function_type_object(dto)

    assert insert_object.nome == "Cliente Teste"
    assert isinstance(insert_object.enderecos, list)
    assert len(insert_object.enderecos) == 2
    assert all(
        isinstance(item, AddressInsertType) for item in insert_object.enderecos
    )
    assert insert_object.enderecos[0].rua == "Rua A"
    assert insert_object.enderecos[1].numero == "20"
    assert isinstance(insert_object.documento, DocumentInsertType)
    assert insert_object.documento.numero == "123"


def test_build_update_function_type_object_with_mapped_fields():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        DummyDTO,
        DummyEntity,
        update_function_type_class=DummyUpdateType,
        update_function_name="teste.fn_dummy_upd",
    )

    dto = DummyDTO()
    dto.valor = 2
    dto.descricao = "nova descricao"

    update_object = service._build_update_function_type_object(dto)

    assert update_object.valor_update == 12
    assert update_object.descricao_func == "NOVA DESCRICAO"


def test_build_update_function_type_object_with_relations():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        CustomerWithRelationsDTO,
        DummyEntity,
        update_function_type_class=CustomerWithRelationsUpdateType,
        update_function_name="teste.fn_cliente_relacionado_upd",
    )

    dto = CustomerWithRelationsDTO()
    dto.nome = "Cliente Teste"

    addr1 = AddressDTO()
    addr1.rua = "Rua A"
    addr1.numero = "10"

    dto.enderecos = [addr1]

    document = DocumentDTO()
    document.numero = "123"
    document.tipo = "CPF"
    dto.documento = document

    update_object = service._build_update_function_type_object(dto)

    assert isinstance(update_object.enderecos_update, list)
    assert len(update_object.enderecos_update) == 1
    assert isinstance(update_object.enderecos_update[0], AddressUpdateType)
    assert update_object.enderecos_update[0].rua == "Rua A"
    assert isinstance(update_object.documento_update, DocumentUpdateType)
    assert update_object.documento_update.numero == "123"


@UpdateFunctionType(type_name="teste.tdummy_args_upd")
class DummyArgsUpdateType(UpdateFunctionTypeBase):
    valor_update: int = FunctionField()
    grupo_empresarial: uuid.UUID = FunctionField(
        binding_source="args.grupo_empresarial"
    )


def test_build_update_function_type_object_with_query_arg_binding():
    app = Flask(__name__)
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        DummyDTO,
        DummyEntity,
        update_function_type_class=DummyArgsUpdateType,
        update_function_name="teste.fn_dummy_args_upd",
    )

    dto = DummyDTO()
    dto.valor = 7

    grupo = str(uuid.uuid4())
    with app.test_request_context(f"/dummy?grupo_empresarial={grupo}"):
        update_object = service._build_update_function_type_object(dto)

    assert update_object.valor_update == 7
    assert update_object.grupo_empresarial == uuid.UUID(grupo)


def test_build_insert_function_type_object_with_literal_null_binding_in_relation():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        CustomerWithRelationsDTO,
        DummyEntity,
        insert_function_type_class=CustomerWithNullRelationInsertType,
        insert_function_name="teste.fn_cliente_relacionado_null",
    )

    dto = CustomerWithRelationsDTO()
    dto.nome = "Cliente Teste"

    addr = AddressDTO()
    addr.rua = "Rua Nula"
    addr.numero = "10"
    dto.enderecos = [addr]

    insert_object = service._build_insert_function_type_object(dto)

    assert isinstance(insert_object.enderecos, list)
    assert len(insert_object.enderecos) == 1
    assert insert_object.enderecos[0].rua == "Rua Nula"
    assert insert_object.enderecos[0].idpessoa is None


def test_build_insert_function_type_object_with_entity_field_alias_in_relation():
    service = ServiceBase(
        FakeInjector(),
        DummyDAO(),
        CustomerWithEntityFieldAliasDTO,
        DummyEntity,
        insert_function_type_class=CustomerWithEntityFieldAliasInsertType,
        insert_function_name="teste.fn_cliente_relacionado_alias",
    )

    dto = CustomerWithEntityFieldAliasDTO()
    dto.nome = "Cliente Alias"

    addr = AddressAliasDTO()
    addr.tipo_logradouro = "AV"
    addr.padrao = "SIM"
    dto.enderecos = [addr]

    insert_object = service._build_insert_function_type_object(dto)

    assert isinstance(insert_object.enderecos, list)
    assert len(insert_object.enderecos) == 1
    assert insert_object.enderecos[0].tipologradouro == "AV"
    assert insert_object.enderecos[0].enderecopadrao == "SIM"


def test_sql_function_type_with_relations():
    dao = DAOBaseSaveByFunction(None, DummyEntity)

    insert_object = CustomerWithRelationsInsertType()
    insert_object.nome = "Cliente SQL"

    endereco_insert = AddressInsertType()
    endereco_insert.rua = "Rua SQL"
    endereco_insert.numero = "99"
    insert_object.enderecos = [endereco_insert]

    document_insert = DocumentInsertType()
    document_insert.numero = "321"
    document_insert.tipo = "CNPJ"
    insert_object.documento = document_insert

    declarations, assignments, values_map = dao._sql_function_type(
        insert_object
    )

    assert "VAR_ROOT_ENDERECOS_0 teste.tendereco;" in declarations
    assert "VAR_ROOT_DOCUMENTO teste.tdocumento;" in declarations

    assert "VAR_TIPO.nome = :root_nome;" in assignments
    assert "VAR_TIPO.enderecos = ARRAY[]::teste.tendereco[];" in assignments
    assert (
        "VAR_ROOT_ENDERECOS_0.rua = :root_enderecos_0_rua;" in assignments
    )
    assert (
        "VAR_TIPO.enderecos = array_append(VAR_TIPO.enderecos, VAR_ROOT_ENDERECOS_0);"
        in assignments
    )
    assert "VAR_TIPO.documento = VAR_ROOT_DOCUMENTO;" in assignments

    assert values_map["root_nome"] == "Cliente SQL"
    assert values_map["root_enderecos_0_rua"] == "Rua SQL"
    assert values_map["root_documento_numero"] == "321"
