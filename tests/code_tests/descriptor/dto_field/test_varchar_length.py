import re

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField, DTOFieldFilter, FilterOperator
from rest_lib.dto.dto_base import DTOBase

from rest_lib.decorator.entity import Entity

from rest_lib.dao.dao_base import DAOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.service.service_base import ServiceBase


@DTO()
class DTOTeste(DTOBase):

    valor: str = DTOField(
        resume=True,
        filters=[
            DTOFieldFilter(
                name="valor_length_maior_igual",
                operator=FilterOperator.LENGTH_GREATER_OR_EQUAL_THAN,
            ),
            DTOFieldFilter(
                name="valor_length_menor_igual",
                operator=FilterOperator.LENGTH_LESS_OR_EQUAL_THAN,
            ),
        ],
    )


@Entity(table_name="teste_entity", pk_field="num", default_order_fields=["num"])
class EntityTeste(EntityBase):
    valor: str = None


class DBAdapterTeste:
    last_sql: str = None

    def execute_query_to_model(self, sql: str, model_class: object, **kwargs) -> list:
        self.last_sql = sql
        entity = EntityTeste()
        entity.valor = "oi"

        return [entity]


class TestAutoIncrement:

    def test_length_maior_igual(self):
        matcher = re.compile(r"length\(.+\) >=")

        dbadapter = DBAdapterTeste()
        service = ServiceBase(
            injector_factory=None,
            dao=DAOBase(db=dbadapter, entity_class=EntityTeste),
            dto_class=DTOTeste,
            entity_class=EntityTeste,
            dto_post_response_class=DTOTeste,
        )
        service.list(
            after=None,
            limit=50,
            fields={"root": set(["valor"])},
            filters={"valor_length_maior_igual": 2},
            order_fields=None,
        )

        match = matcher.search(dbadapter.last_sql)

        assert match is not None

    def test_length_menor_igual(self):
        matcher = re.compile(r"length\(.+\) <=")

        dbadapter = DBAdapterTeste()
        service = ServiceBase(
            injector_factory=None,
            dao=DAOBase(db=dbadapter, entity_class=EntityTeste),
            dto_class=DTOTeste,
            entity_class=EntityTeste,
            dto_post_response_class=DTOTeste,
        )
        service.list(
            after=None,
            limit=50,
            fields={"root": set(["valor"])},
            filters={"valor_length_menor_igual": 2, "valor": "oi"},
            order_fields=None,
        )

        match = matcher.search(dbadapter.last_sql)

        assert match is not None
