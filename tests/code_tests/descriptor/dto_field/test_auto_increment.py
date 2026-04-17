import uuid

from typing import List
from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.conjunto_type import ConjuntoType
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.dto.dto_base import DTOBase

from rest_lib.decorator.entity import Entity

from rest_lib.dao.dao_base import DAOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.exception import NotFoundException
from rest_lib.service.service_base import ServiceBase
from rest_lib.util.join_aux import JoinAux


@DTO()
class DTOTeste(DTOBase):

    num: int = DTOField(
        auto_increment={
            "sequence_name": "NOME_DA_SEQUENCIA",
            "template": "{seq}",
            "group": ["field1", "field2"],
            "start_value": 1,
            "db_managed": False,
        }
    )
    num2: int = DTOField(
        auto_increment={
            "sequence_name": "NOME_DA_SEQUENCIA",
            "template": "{seq}",
            "group": ["field1", "field2"],
            "start_value": 1,
            "db_managed": True,
        }
    )


@Entity(table_name="teste_entity", pk_field="num", default_order_fields=["num"])
class EntityTeste(EntityBase):
    num: int = None
    num2: int = None


class DAOTest(DAOBase):
    def __init__(self, da, entity_class):
        super().__init__(db=da, entity_class=entity_class)
        self.count = 10

    def insert(self, entity: EntityBase, sql_read_only_fields: List[str] = []):
        return entity

    def next_val(
        self,
        sequence_base_name: str,
        group_fields: List[str],
        start_value: int = 1,
    ):
        self.count += 1
        return self.count

    def begin(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def get(
        self,
        key_field: str,
        id: uuid.UUID,
        fields: List[str] = None,
        filters=None,
        conjunto_type: ConjuntoType = None,
        conjunto_field: str = None,
        joins_aux: List[JoinAux] = None,
        override_data: bool = False,
    ) -> EntityBase:
        raise NotFoundException("")

    def entity_exists(entity, aditional_entity_filters):
        print("entity_exists called")
        return False


class TestAutoIncrement:
    def test_auto_increment_normal_configure(self):
        field = DTOTeste.fields_map["num"]
        assert field.auto_increment is not None
        assert field.auto_increment.sequence_name == "NOME_DA_SEQUENCIA"
        assert field.auto_increment.template == "{seq}"
        assert field.auto_increment.group == ["field1", "field2"]
        assert field.auto_increment.start_value == 1
        assert field.auto_increment.db_managed is False

    def test_auto_increment_db_managed_configure(self):
        field = DTOTeste.fields_map["num2"]
        assert field.auto_increment is not None
        assert field.auto_increment.sequence_name is None
        assert field.auto_increment.template is None
        assert field.auto_increment.group is None
        assert field.auto_increment.start_value is None
        assert field.auto_increment.db_managed is True

    def test_fulfilment(self):
        dto = DTOTeste()
        service = ServiceBase(
            injector_factory=None,
            dao=DAOTest(da=None, entity_class=EntityTeste),
            dto_class=DTOTeste,
            entity_class=EntityTeste,
            dto_post_response_class=DTOTeste,
        )
        dto_response = service.insert(dto)
        assert dto_response.num == 11
        assert dto_response.num2 is None
