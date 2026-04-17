import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rest_lib.controller.get_route import GetRoute
from rest_lib.controller.list_route import ListRoute
from rest_lib.decorator.dto import DTO
from rest_lib.decorator.entity import Entity
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.entity_field import EntityField
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.settings import application


class FakeInjectorFactory:
    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class ExpandRecordingService:
    def __init__(self, payload):
        self.payload = payload
        self.last_fields = None
        self.last_expands = None

    def get(
        self,
        id,
        partition_fields,
        fields,
        expands=None,
        function_params=None,
        function_object=None,
        function_name=None,
        custom_json_response=False,
    ):
        self.last_fields = fields
        self.last_expands = expands
        return self.payload

    def list(
        self,
        after,
        limit,
        fields,
        order_fields,
        filters,
        search_query=None,
        return_hidden_fields=None,
        expands=None,
        function_params=None,
        function_object=None,
        function_name=None,
        custom_json_response=False,
    ):
        self.last_fields = fields
        self.last_expands = expands
        return self.payload


@DTO()
class SampleDTO(DTOBase):
    id: int = DTOField(pk=True)
    name: str = DTOField()
    auto_increment_fields = {}


@Entity(table_name="public.sample", pk_field="id", default_order_fields=["id"])
class SampleEntity(EntityBase):
    id: int = EntityField()
    name: str = EntityField()


def test_get_route_merges_expand_into_fields():
    payload = {"ok": True}
    service = ExpandRecordingService(payload)

    class GetRouteUnderTest(GetRoute):
        def _get_service(self, factory):
            return service

    route = GetRouteUnderTest(
        url="/samples/<id>",
        http_method="GET",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        get_function_name="fn_get",
        custom_json_response=True,
    )

    with application.test_request_context(
        "/samples/1?expand=child(detail)", method="GET"
    ):
        body, status, _ = route.handle_request(id="1")

    assert status == 200
    assert json.loads(body) == payload

    fields = service.last_fields
    assert "child" in fields["root"]
    assert "child" in fields
    assert "detail" in fields["child"]["root"]


def test_list_route_merges_expand_into_fields():
    payload = [{"id": 1}]
    service = ExpandRecordingService(payload)

    class ListRouteUnderTest(ListRoute):
        def _get_service(self, factory):
            return service

    route = ListRouteUnderTest(
        url="/samples",
        http_method="GET",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        list_function_name="fn_list",
        custom_json_response=True,
    )

    with application.test_request_context(
        "/samples?expand=items(detail)", method="GET"
    ):
        body, status, _ = route.handle_request()

    assert status == 200
    assert json.loads(body) == payload

    fields = service.last_fields
    assert "items" in fields["root"]
    assert "items" in fields
    assert "detail" in fields["items"]["root"]
