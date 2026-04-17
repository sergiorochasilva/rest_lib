from unittest.mock import Mock

from rest_lib.dao.dao_base_search import DAOBaseSearch  # type: ignore
from rest_lib.decorator.entity import Entity  # type: ignore
from rest_lib.descriptor.entity_field import EntityField  # type: ignore
from rest_lib.entity.entity_base import EntityBase  # type: ignore


@Entity(table_name="test.table", pk_field="id", default_order_fields=["id"])
class SearchEntity(EntityBase):  # pylint: disable=too-few-public-methods
    id: int = EntityField()
    nome: str = EntityField()


class DummyDAO(DAOBaseSearch):  # pylint: disable=too-few-public-methods
    pass


def test_make_search_sql_wraps_column_and_value_with_unaccent():
    dao = DummyDAO(db=Mock(), entity_class=SearchEntity)
    # pylint: disable-next=protected-access
    search_map, search_where = dao._make_search_sql(
        "ação", ["nome"], SearchEntity()
    )
    expected_fragment = (
        "upper(unaccent(CAST(t0.nome AS varchar))) "
        "like upper(unaccent(:shf_nome_0))"
    )
    assert expected_fragment in search_where
    assert search_map["shf_nome_0"] == "%acao%"
