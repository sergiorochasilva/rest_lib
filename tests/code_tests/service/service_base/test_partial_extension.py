from unittest.mock import Mock

from rest_lib.decorator.dto import DTO
from rest_lib.decorator.entity import Entity
from rest_lib.decorator.update_function_type import UpdateFunctionType
from rest_lib.descriptor.dto_aggregator import DTOAggregator
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_list_field import DTOListField
from rest_lib.descriptor.function_field import FunctionField
from rest_lib.descriptor.function_relation_field import FunctionRelationField
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import UpdateFunctionTypeBase
from rest_lib.service.service_base import ServiceBase
from rest_lib.exception import NotFoundException
from rest_lib.settings import ENV_MULTIDB


@Entity(
    table_name="produto",
    pk_field="id",
    default_order_fields=["id"],
)
class ProdutoEntity(EntityBase):
    id: int = None
    codigo: str = None
    tenant: int = None


@DTO()
class ProdutoDTO(DTOBase):
    id: int = DTOField(pk=True, resume=True)
    codigo: str = DTOField(resume=True)
    tenant: int = DTOField(partition_data=True)


@Entity(
    partial_of=ProdutoEntity,
    partial_table_name="farmaco",
)
class FarmacoEntity(EntityBase):
    id_produto: int = None
    registro_anvisa: str = None
    tenant: int = None


@DTO(
    partial_of={
        "dto": ProdutoDTO,
        "relation_field": "id_produto",
        "related_entity_field": "id",
    }
)
class FarmacoDTO(DTOBase):
    id_produto: int = DTOField()
    registro_anvisa: str = DTOField()
    tenant: int = DTOField(partition_data=True)


@DTO()
class PessoaBaseDTO(DTOBase):
    id: int = DTOField(pk=True)
    indicador_inscricao_estadual: str = DTOField()


@DTO(
    partial_of={
        "dto": PessoaBaseDTO,
        "relation_field": "id_pessoa",
        "related_entity_field": "id",
    }
)
class TecnicoBaseDTO(DTOBase):
    id_pessoa: int = DTOField()
    tecnico_ativado: bool = DTOField()


@DTO(
    partial_of={
        "dto": TecnicoBaseDTO,
        "relation_field": "id_pessoa",
        "related_entity_field": "id",
    }
)
class ProfissionalChainDTO(DTOBase):
    id_pessoa: int = DTOField()
    foto: str = DTOField()


@UpdateFunctionType(type_name="teste.t_profissional_chain_upd")
class ProfissionalChainUpdateType(UpdateFunctionTypeBase):
    indicador_inscricao_estadual: str = FunctionField()
    tecnico_ativado: bool = FunctionField()
    foto: str = FunctionField()


@DTO()
class SituacaoFiscalDTO(DTOBase):
    indicador_inscricao_estadual: str = DTOField()
    inscricao_estadual: str = DTOField()


@DTO()
class TecnicoWithAggregatorDTO(DTOBase):
    id: int = DTOField(pk=True)
    tecnico_ativado: bool = DTOField()
    situacao_fiscal: SituacaoFiscalDTO = DTOAggregator(SituacaoFiscalDTO)


@DTO(
    partial_of={
        "dto": TecnicoWithAggregatorDTO,
        "relation_field": "id_pessoa",
        "related_entity_field": "id",
    }
)
class ProfissionalWithAggregatorDTO(DTOBase):
    id_pessoa: int = DTOField()
    foto: str = DTOField()


@UpdateFunctionType(type_name="teste.t_profissional_aggregator_upd")
class ProfissionalWithAggregatorUpdateType(UpdateFunctionTypeBase):
    indicador_inscricao_estadual: str = FunctionField()
    inscricao_estadual: str = FunctionField()
    tecnico_ativado: bool = FunctionField()
    foto: str = FunctionField()


@DTO()
class EnderecoBaseDTO(DTOBase):
    logradouro: str = DTOField()
    numero: str = DTOField()


@DTO()
class TecnicoWithInheritedRelationsDTO(DTOBase):
    id: int = DTOField(pk=True)
    tecnico_ativado: bool = DTOField()
    enderecos: list[EnderecoBaseDTO] = DTOListField(
        dto_type=EnderecoBaseDTO,
        entity_type=ProdutoEntity,
        related_entity_field="id_pessoa",
    )


@DTO(
    partial_of={
        "dto": TecnicoWithInheritedRelationsDTO,
        "relation_field": "id_pessoa",
        "related_entity_field": "id",
    }
)
class ProfissionalWithInheritedRelationsDTO(DTOBase):
    id_pessoa: int = DTOField()
    foto: str = DTOField()


@UpdateFunctionType(type_name="teste.t_endereco_relacao_upd")
class EnderecoRelationUpdateType(UpdateFunctionTypeBase):
    logradouro: str = FunctionField()
    numero: str = FunctionField()


@UpdateFunctionType(type_name="teste.t_profissional_relacao_upd")
class ProfissionalWithInheritedRelationsUpdateType(UpdateFunctionTypeBase):
    tecnico_ativado: bool = FunctionField()
    foto: str = FunctionField()
    enderecos: list[EnderecoRelationUpdateType] = FunctionRelationField()


def build_service_with_mock():
    dao = Mock()
    dao.list.return_value = []
    dao.get.return_value = FarmacoEntity()
    dao.partial_extension_exists = Mock(return_value=False)
    dao.insert_partial_extension_record = Mock()
    dao.update_partial_extension_record = Mock()
    return ServiceBase(None, dao, FarmacoDTO, FarmacoEntity), dao


def test_partial_list_without_extension_fields_uses_exists_and_no_join():
    service, dao = build_service_with_mock()

    service.list(
        after=None,
        limit=None,
        fields={"root": set()},
        order_fields=None,
        filters={},
    )

    assert dao.list.call_count == 1
    args, kwargs = dao.list.call_args
    joins_aux = kwargs.get("joins_aux")
    assert joins_aux == [] or all(join.alias != "partial_join" for join in joins_aux)
    assert kwargs.get("partial_exists_clause") == ("farmaco", "id", "id_produto")


def test_partial_list_with_extension_field_triggers_join():
    service, dao = build_service_with_mock()

    service.list(
        after=None,
        limit=None,
        fields={"root": {"registro_anvisa"}},
        order_fields=None,
        filters={},
    )

    args, kwargs = dao.list.call_args
    joins_aux = kwargs.get("joins_aux")
    assert joins_aux is not None
    assert any(join.alias == "partial_join" for join in joins_aux)
    assert kwargs.get("partial_exists_clause") is None

    entity_fields = args[2]
    assert "registro_anvisa" not in entity_fields


def test_partial_order_field_triggers_join_and_alias():
    service, dao = build_service_with_mock()

    service.list(
        after=None,
        limit=None,
        fields={"root": set()},
        order_fields=["registro_anvisa desc"],
        filters={},
    )

    args, kwargs = dao.list.call_args
    joins_aux = kwargs.get("joins_aux")
    assert joins_aux is not None
    assert any(join.alias == "partial_join" for join in joins_aux)
    assert kwargs.get("partial_exists_clause") is None

    order_specs = args[3]
    assert len(order_specs) == 1
    spec = order_specs[0]
    assert spec.source.name == "PARTIAL_EXTENSION"
    assert spec.column == "registro_anvisa"
    assert spec.is_desc is True


def test_partial_insert_saves_extension_record():
    service, dao = build_service_with_mock()

    dao.get.side_effect = NotFoundException("not found")
    dao.insert.side_effect = lambda entity, *_: entity
    dao.partial_extension_exists.return_value = False

    dto = FarmacoDTO(id=1, codigo="PROD-1", tenant=42, registro_anvisa="ABC123")

    service.insert(dto)

    dao.insert.assert_called_once()
    dao.partial_extension_exists.assert_called_once_with(
        "farmaco", "id_produto", 1
    )
    dao.insert_partial_extension_record.assert_called_once()

    insert_args, _ = dao.insert_partial_extension_record.call_args
    assert insert_args[0] == "farmaco"
    payload = insert_args[1]
    assert payload["id_produto"] == 1
    assert payload["registro_anvisa"] == "ABC123"    
    ## Verifica se o campo tenant é incluído ou não conforme a configuração
    if ENV_MULTIDB == "false":
        assert payload["tenant"] == 42


def test_partial_update_updates_extension_record():
    service, dao = build_service_with_mock()

    service.get = Mock(
        return_value=FarmacoDTO(
            id=1, codigo="PROD-1", tenant=42, registro_anvisa="OLD"
        )
    )
    dao.update.side_effect = lambda *args, **kwargs: args[2]
    dao.partial_extension_exists.return_value = True

    dto = FarmacoDTO(id=1, codigo="PROD-1", tenant=42, registro_anvisa="NEW")

    service.update(dto, id=1)

    dao.update.assert_called_once()
    dao.update_partial_extension_record.assert_called_once()
    args_call, _ = dao.update_partial_extension_record.call_args
    assert args_call[0] == "farmaco"
    assert args_call[1] == "id_produto"
    assert args_call[2] == 1
    ## Verifica se o campo tenant é incluído ou não conforme a configuração
    if ENV_MULTIDB == "false":
        assert args_call[3] == {"registro_anvisa": "NEW", "tenant": 42}


def test_partial_patch_updates_only_provided_extension_fields():
    service, dao = build_service_with_mock()

    service.get = Mock(
        return_value=FarmacoDTO(
            id=1, codigo="PROD-1", tenant=42, registro_anvisa="OLD"
        )
    )
    dao.update.side_effect = lambda *args, **kwargs: args[2]
    dao.partial_extension_exists.return_value = True

    dto = FarmacoDTO(id=1, registro_anvisa="PATCHED")

    service.partial_update(dto, id=1)

    dao.update_partial_extension_record.assert_called_once()
    args_call, _ = dao.update_partial_extension_record.call_args
    assert args_call[3] == {"registro_anvisa": "PATCHED"}


def test_partial_of_inherits_transitive_parent_fields_for_update_function_mapping():
    class DummyDAO:
        _db = None

    service = ServiceBase(
        None,
        DummyDAO(),
        ProfissionalChainDTO,
        ProdutoEntity,
        update_function_type_class=ProfissionalChainUpdateType,
        update_function_name="teste.fn_profissional_chain_upd",
    )

    dto = ProfissionalChainDTO(
        indicador_inscricao_estadual="ISENTO",
        tecnico_ativado=True,
        foto="avatar.png",
    )

    assert hasattr(dto, "indicador_inscricao_estadual")

    update_object = service._build_update_function_type_object(dto)

    assert update_object.indicador_inscricao_estadual == "ISENTO"
    assert update_object.tecnico_ativado is True
    assert update_object.foto == "avatar.png"


def test_partial_of_maps_aggregator_fields_into_update_function_mapping():
    class DummyDAO:
        _db = None

    service = ServiceBase(
        None,
        DummyDAO(),
        ProfissionalWithAggregatorDTO,
        ProdutoEntity,
        update_function_type_class=ProfissionalWithAggregatorUpdateType,
        update_function_name="teste.fn_profissional_aggregator_upd",
    )

    dto = ProfissionalWithAggregatorDTO(
        tecnico_ativado=True,
        foto="avatar.png",
        situacao_fiscal={
            "indicador_inscricao_estadual": "ISENTO",
            "inscricao_estadual": "123",
        },
    )

    update_object = service._build_update_function_type_object(dto)

    assert update_object.indicador_inscricao_estadual == "ISENTO"
    assert update_object.inscricao_estadual == "123"
    assert update_object.tecnico_ativado is True
    assert update_object.foto == "avatar.png"


def test_partial_of_infers_relation_function_type_from_update_function():
    class DummyDAO:
        _db = None

    service = ServiceBase(
        None,
        DummyDAO(),
        ProfissionalWithInheritedRelationsDTO,
        ProdutoEntity,
        update_function_type_class=ProfissionalWithInheritedRelationsUpdateType,
        update_function_name="teste.fn_profissional_relacao_upd",
    )

    dto = ProfissionalWithInheritedRelationsDTO(
        tecnico_ativado=True,
        foto="avatar.png",
        enderecos=[{"logradouro": "Rua A", "numero": "10"}],
    )

    update_object = service._build_update_function_type_object(dto)

    assert update_object.tecnico_ativado is True
    assert update_object.foto == "avatar.png"
    assert len(update_object.enderecos) == 1
    assert isinstance(update_object.enderecos[0], EnderecoRelationUpdateType)
    assert update_object.enderecos[0].logradouro == "Rua A"
    assert update_object.enderecos[0].numero == "10"
