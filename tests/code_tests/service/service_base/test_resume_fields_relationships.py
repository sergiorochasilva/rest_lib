from unittest.mock import Mock

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.dto_list_field import DTOListField
from rest_lib.descriptor.dto_object_field import DTOObjectField, EntityRelationOwner
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.service.service_base import ServiceBase


class TelefoneEntity(EntityBase):
    id: int = None
    contato_id: int = None
    numero: str = None
    ddd: str = None


class ContatoEntity(EntityBase):
    id: int = None
    pessoa_id: int = None
    nome: str = None


class DocumentoEntity(EntityBase):
    id: int = None
    codigo: str = None


class PessoaEntity(EntityBase):
    id: int = None
    doc_id: int = None


@DTO()
class TelefoneDTO(DTOBase):
    numero: str = DTOField(resume=False)
    ddd: str = DTOField()


@DTO()
class DocumentoDTO(DTOBase):
    codigo: str = DTOField(resume=True)
    descricao: str = DTOField()


@DTO()
class ContatoDTO(DTOBase):
    id: int = DTOField(pk=True)
    nome: str = DTOField(resume=True)
    telefones: list = DTOListField(
        dto_type=TelefoneDTO,
        entity_type=TelefoneEntity,
        related_entity_field="contato_id",
        relation_key_field="id",
    )


@DTO()
class PessoaDTO(DTOBase):
    pk_field = "id"

    id: int = DTOField(pk=True, resume=True)
    nome: str = DTOField(resume=True)
    doc_id: int = DTOField()
    contatos: list = DTOListField(
        dto_type=ContatoDTO,
        entity_type=ContatoEntity,
        related_entity_field="pessoa_id",
        relation_key_field="id",
        resume_fields=["nome", "telefones.numero"],
    )
    documento_principal: DocumentoDTO = DTOObjectField(
        entity_type=DocumentoEntity,
        relation_field="doc_id",
        entity_relation_owner=EntityRelationOwner.SELF,
        resume_fields=["codigo"],
    )


def build_service():
    injector = Mock()
    dao = Mock()
    dao.begin.return_value = None
    dao.commit.return_value = None
    return ServiceBase(injector, dao, PessoaDTO, PessoaEntity)


def test_resolving_fields_includes_resume_relationships():
    service = build_service()

    resolved = service._resolving_fields(None)

    assert "contatos" in resolved["root"]
    assert "documento_principal" in resolved["root"]

    contatos_fields = resolved["contatos"]
    assert "nome" in contatos_fields["root"]
    assert "telefones" in contatos_fields["root"]

    telefones_fields = contatos_fields["telefones"]
    assert "numero" in telefones_fields["root"]

    documento_fields = resolved["documento_principal"]
    assert "codigo" in documento_fields["root"]


def test_convert_to_dict_uses_resume_fields_tree():
    pessoa = PessoaDTO(
        id=1,
        nome="Fulano",
        doc_id=77,
        documento_principal={"codigo": "DOC123", "descricao": "Documento completo"},
        contatos=[
            {
                "nome": "Contato X",
                "telefones": [
                    {"numero": "1111-2222", "ddd": "11"},
                ],
            }
        ],
    )

    result = pessoa.convert_to_dict()

    assert "contatos" in result
    contatos = result["contatos"]
    assert contatos
    contato = contatos[0]
    assert contato["nome"] == "Contato X"
    assert "telefones" in contato

    telefone = contato["telefones"][0]
    assert telefone["numero"] == "1111-2222"
    assert "ddd" not in telefone

    documento = result["documento_principal"]
    assert documento["codigo"] == "DOC123"
    assert "descricao" not in documento
