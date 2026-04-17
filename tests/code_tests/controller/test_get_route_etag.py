import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rest_lib.controller.get_route import GetRoute
from rest_lib.controller.route_base import RouteBase
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


class RecordingService:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

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
        self.calls.append(
            {
                "id": id,
                "partition_fields": partition_fields,
                "fields": fields,
                "expands": expands,
                "function_params": function_params,
                "function_object": function_object,
                "function_name": function_name,
                "custom_json_response": custom_json_response,
            }
        )
        index = len(self.calls) - 1
        if index < len(self.responses):
            return self.responses[index]
        return self.responses[-1]


@DTO(etag_fields={"version"})
class SampleDTO(DTOBase):
    id: int = DTOField(pk=True, resume=True)
    version: str = DTOField()
    name: str = DTOField()


@Entity(table_name="public.sample", pk_field="id", default_order_fields=["id"])
class SampleEntity(EntityBase):
    id: int = EntityField()
    version: str = EntityField()
    name: str = EntityField()


def build_route(service):
    class GetRouteUnderTest(GetRoute):
        def _get_service(self, factory):
            return service

    return GetRouteUnderTest(
        url="/samples/<id>",
        http_method="GET",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
    )


def build_dto(version, name="sample"):
    return SampleDTO(id=1, version=version, name=name, escape_validator=True)


def build_etag_header(dto):
    headers = {}
    RouteBase.add_etag_header_if_needed(headers, dto)
    return headers.get("ETag")


def build_etag_value(dto):
    return RouteBase.get_etag_value(dto)


def test_get_route_returns_etag_header_on_success():
    dto = build_dto("v1")
    service = RecordingService([dto])
    route = build_route(service)

    with application.test_request_context("/samples/1", method="GET"):
        body, status, headers = route.handle_request(id="1")

    assert status == 200
    assert headers.get("ETag") == build_etag_header(dto)
    assert len(service.calls) == 1
    assert json.loads(body)["id"] == 1


def test_get_route_if_none_match_returns_304_and_skips_full_fetch():
    dto = build_dto("v1")
    service = RecordingService([dto])
    route = build_route(service)

    with application.test_request_context(
        "/samples/1",
        method="GET",
        headers={
            "If-None-Match": RouteBase.quote_and_escape_string(
                build_etag_value(dto)
            )
        },
    ):
        body, status, headers = route.handle_request(id="1")

    assert status == 304
    assert body == ""
    assert headers.get("ETag") == build_etag_header(dto)
    assert len(service.calls) == 1
    assert service.calls[0]["fields"]["root"] == {"version", "id"}


def test_get_route_if_none_match_mismatch_fetches_full_data_and_sets_etag():
    dto_initial = build_dto("v1")
    dto_full = build_dto("v2", name="full")
    service = RecordingService([dto_initial, dto_full])
    route = build_route(service)

    with application.test_request_context(
        "/samples/1",
        method="GET",
        headers={"If-None-Match": '"v0"'},
    ):
        body, status, headers = route.handle_request(id="1")

    assert status == 200
    assert headers.get("ETag") == build_etag_header(dto_full)
    assert len(service.calls) == 2
    assert "version" in service.calls[1]["fields"]["root"]
    assert json.loads(body)["id"] == 1


def test_get_route_if_none_match_multiple_values_returns_304():
    dto = build_dto("v1")
    service = RecordingService([dto])
    route = build_route(service)

    with application.test_request_context(
        "/samples/1",
        method="GET",
        headers={
            "If-None-Match": (
                f'"v0", {RouteBase.quote_and_escape_string(build_etag_value(dto))}, "v2"'
            )
        },
    ):
        body, status, headers = route.handle_request(id="1")

    assert status == 304
    assert body == ""
    assert headers.get("ETag") == build_etag_header(dto)
    assert len(service.calls) == 1
