"""
Testes para funcionaldiade de retrive_object_fields da classe ServiceBase
"""

from typing import Union
import unittest
from unittest.mock import Mock #, patch, MagicMock
import pytest


from rest_lib.service.service_base import ServiceBase
from rest_lib.descriptor.dto_object_field import DTOObjectField, EntityRelationOwner
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import DTOListFieldConfigException
from rest_lib.decorator.dto import DTO
from rest_lib.decorator.entity import Entity
from rest_lib.descriptor.dto_field import DTOField

@Entity(
    table_name="mock_table",
    pk_field="id",
    default_order_fields=["id"],
)
class MockEntity(EntityBase):
    id: int = None

@Entity(
    table_name="mock_related_table",
    pk_field="id",
    default_order_fields=["id"],
)
class MockRelatedEntity(EntityBase):
    id: int = None


@DTO()
class MockRelatedDTO(DTOBase):
    """DTO relacionado mock para testes"""
    pk_field = "id"

    id: int = DTOField(pk=True)
    name: str = DTOField()

    def __init__(
        self,
        entity: Union[EntityBase, dict] = None,
        escape_validator: bool = False,
        generate_default_pk_value: bool = True,
        validate_read_only: bool = False,
        kwargs_as_entity: bool = False,
        **kwargs,
    ):
        super().__init__(entity, escape_validator, generate_default_pk_value, validate_read_only, kwargs_as_entity, **kwargs)
        # Adicionando atributos que podem ser passados no __init__
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        #self.company_id = kwargs.get('company_id')


@DTO()
class MockDTO(DTOBase):
    """DTO mock para testes"""
    pk_field = "id"

    id: int = DTOField(pk=True)
    user_id: int = DTOField()
    related_user: MockRelatedDTO = DTOObjectField(
        resume=False,
        entity_type=MockEntity,
        relation_field='user_id',
        entity_relation_owner=EntityRelationOwner.SELF
    )
    company_id: int = DTOField()
    related_company: MockRelatedDTO = DTOObjectField(
        resume=False,
        entity_type=MockEntity,
        relation_field='id',
        entity_relation_owner=EntityRelationOwner.OTHER
    )

    def __init__(
        self,
        entity: Union[EntityBase, dict] = None,
        escape_validator: bool = False,
        generate_default_pk_value: bool = True,
        validate_read_only: bool = False,
        kwargs_as_entity: bool = False,
        **kwargs,
    ):
        super().__init__(entity, escape_validator, generate_default_pk_value, validate_read_only, kwargs_as_entity, **kwargs)
        # Inicializando atributos que serão usados nos testes
        self.related_user = None
        self.related_company = None
        # Adicionando atributos que podem ser passados no __init__
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.company_id = kwargs.get('company_id')


class MockObjectField:
    """Mock para DTOObjectField"""
    def __init__(self, relation_field: str, owner: EntityRelationOwner):
        self.relation_field = relation_field
        self.entity_relation_owner = owner
        self.entity_type = MockEntity
        self.expected_type = MockRelatedDTO


class TestRetrieveObjectFields(unittest.TestCase):
    """Testes para o método _retrieve_object_fields otimizado"""

    def mock_execute_query_to_model(self, sql, model_class, **kwargs):

        return [ self.related_list[id] for id in self.related_list if id == kwargs['id'] ]


    def setUp(self):
        """Configuração inicial para cada teste"""
        # Mock do injeusrr factory
        self.mock_injector_factory = Mock()
        self.mock_db_adapter = Mock()
        self.mock_db_adapter.execute_query_to_model.side_effect = self.mock_execute_query_to_model
        self.mock_injector_factory.db_adapter.return_value = self.mock_db_adapter

        # Mock do DAO
        self.mock_dao = Mock()


        # MockDTO.object_fields_map = {
        #     "related_user": MockObjectField("user_id", EntityRelationOwner.SELF),
        #     "related_company": MockObjectField("company_id", EntityRelationOwner.OTHER),
        # }

        # Instância do ServiceBase para testes
        self.service = ServiceBase(
            self.mock_injector_factory,
            self.mock_dao,
            MockDTO,
            MockEntity
        )

        # DTOs de teste
        self.dto1 = MockDTO(id="1", user_id=101, company_id=201)
        self.dto2 = MockDTO(id="2", user_id=102, company_id=202)
        self.dto3 = MockDTO(id="3", user_id=103, company_id=203)

        self.dto_list = [self.dto1, self.dto2, self.dto3]

        # Users
        usr1 = MockRelatedEntity()
        usr1.id = 101
        usr1.name = "Company 1"

        usr2 = MockRelatedEntity()
        usr2.id = 102
        usr2.name = "Company 2"

        usr3 = MockRelatedEntity()
        usr3.id = 103
        usr3.name = "Company 3"

        # Companies
        cmp1 = MockRelatedEntity()
        cmp1.id = 201
        cmp1.name = "Company 1"

        cmp2 = MockRelatedEntity()
        cmp2.id = 202
        cmp2.name = "Company 2"

        cmp3 = MockRelatedEntity()
        cmp3.id = 203
        cmp3.name = "Company 3"

        self.related_list = {
            usr1.id : usr1,
            usr2.id : usr2,
            usr3.id : usr3,
            cmp1.id : cmp1,
            cmp2.id : cmp2,
            cmp3.id : cmp3
        }

        # Fields para teste
        self.fields = {
            "root": {"id", "related_user", "related_company"}
        }

        # Partition fields
        self.partition_fields = {"tenant_id": "tenant1"}

    def test_retrieve_object_fields_empty_list(self):
        """Testa comportamento com lista vazia"""
        self.service._retrieve_object_fields([], self.fields, self.partition_fields)

        assert self.dto1.related_user is None
        assert self.dto1.related_company is None
        assert self.dto2.related_user is None
        assert self.dto2.related_company is None
        assert self.dto3.related_user is None
        assert self.dto3.related_company is None

        # Não deve gerar erro e não deve fazer chamadas ao banco

    def test_retrieve_object_fields_no_object_fields(self):
        """Testa comportamento quando não há campos de objeto"""
        # Criando DTO sem campos de objeto
        dto_without_objects = MockDTO(id="1")
        dto_without_objects.object_fields_map = {}

        self.service._retrieve_object_fields(
            [dto_without_objects],
            self.fields,
            self.partition_fields
        )

        assert dto_without_objects.related_user is None
        assert dto_without_objects.related_company is None
        # Não deve gerar erro

    def test_retrieve_object_fields_field_not_in_root(self):
        """Testa comportamento quando campo não está em fields['root']"""
        fields_without_objects = {"root": {"other_field"}}

        self.service._retrieve_object_fields(
            self.dto_list,
            fields_without_objects,
            self.partition_fields
        )

        assert self.dto1.related_user is None
        assert self.dto1.related_company is None
        assert self.dto2.related_user is None
        assert self.dto2.related_company is None
        assert self.dto3.related_user is None
        assert self.dto3.related_company is None

        # Não deve fazer chamadas ao banco

    def test_retrieve_object_fields_entity_type_none(self):
        """Testa comportamento quando entity_type é None"""
        # Modificando um campo para ter entity_type None
        self.dto1.object_fields_map["related_user"].entity_type = None

        self.service._retrieve_object_fields(
            self.dto_list,
            self.fields,
            self.partition_fields
        )

        assert self.dto1.related_user is None
        assert self.dto1.related_company is None
        assert self.dto2.related_user is None
        assert self.dto2.related_company is None
        assert self.dto3.related_user is None
        assert self.dto3.related_company is None
        # Não deve fazer chamadas ao banco

    def test_retrieve_object_fields_pk_field_none(self):
        """Testa comportamento quando pk_field é None"""
        # Modificando o DTO para ter pk_field None
        original_pk_field = self.service._dto_class.pk_field
        self.service._dto_class.pk_field = None

        try:
            with pytest.raises(DTOListFieldConfigException) as excinfo:
                self.service._retrieve_object_fields(
                    self.dto_list,
                    self.fields,
                    self.partition_fields
                )
            assert "PK field not found in class: <class 'test_retrieve_object_fields.MockDTO'>" in str(excinfo.value)

        finally:
            # Restaurando o valor original
            self.service._dto_class.pk_field = original_pk_field

    def test_retrieve_object_fields_self_relation_with_none_values(self):
        """Testa comportamento quando alguns valores de relacionamento são None"""
        # Modificando alguns DTOs para ter valores None
        self.dto1.user_id = None
        self.dto3.user_id = None

        # O método deve processar sem erro, mesmo com valores None
        self.service._retrieve_object_fields(
            self.dto_list,
            self.fields,
            self.partition_fields
        )

        # Verificando que os campos ficaram None para os DTOs com valores None
        self.assertIsNone(getattr(self.dto1, "related_user"))
        self.assertIsNone(getattr(self.dto3, "related_user"))


    def test_retrieve_object_fields_error_handling(self):
        """Testa tratamento de erros"""
        # Testando com DTOs que não têm os campos necessários
        dto_invalid = MockDTO(id="1")  # Sem user_id e company_id

        # O método deve processar sem erro
        self.service._retrieve_object_fields(
            [dto_invalid],
            self.fields,
            self.partition_fields
        )

        # Os campos devem ficar None
        self.assertIsNone(getattr(dto_invalid, "related_user"))
        self.assertIsNone(getattr(dto_invalid, "related_company"))


if __name__ == '__main__':
    unittest.main()