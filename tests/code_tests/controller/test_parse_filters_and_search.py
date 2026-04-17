import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from rest_lib.controller.route_base import RouteBase
from rest_lib.dto.dto_base import DTOBase
from rest_lib.exception import MissingParameterException


class DummyDTO(DTOBase):
    partition_fields = {"tenant_id"}


def test_parse_filters_and_search_extracts_filters_and_search_query():
    args = {
        "Search": "term",
        "name": "Alice",
        "status": "active",
        "limit": "20",
        "after": "cursor",
        "offset": "0",
        "fields": "id,name",
        "expand": "emails",
        "tenant_id": "tenant-1",
    }

    extra_filters = {"from_kwargs": "kw"}

    filters, search_query = RouteBase.parse_filters_and_search(
        DummyDTO, args, extra_filters
    )

    assert search_query == "term"
    assert filters == {
        "from_kwargs": "kw",
        "name": "Alice",
        "status": "active",
        "tenant_id": "tenant-1",
    }
    assert extra_filters == {"from_kwargs": "kw"}


def test_parse_filters_and_search_requires_partition_fields():
    args = {"name": "Alice"}

    with pytest.raises(MissingParameterException) as excinfo:
        RouteBase.parse_filters_and_search(DummyDTO, args)

    assert "tenant_id" in str(excinfo.value)
