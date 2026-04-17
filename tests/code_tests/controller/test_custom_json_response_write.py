import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rest_lib.controller.delete_route import DeleteRoute
from rest_lib.controller.patch_route import PatchRoute
from rest_lib.controller.post_route import PostRoute
from rest_lib.controller.put_route import PutRoute
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


class ResponseService:
    def __init__(self, payload):
        self.payload = payload

    def insert(
        self,
        dto,
        aditional_filters=None,
        custom_before_insert=None,
        custom_after_insert=None,
        retrieve_after_insert=False,
        function_name=None,
        custom_json_response=False,
        retrieve_fields=None,
    ):
        return self.payload

    def update(
        self,
        dto,
        id,
        aditional_filters=None,
        custom_before_update=None,
        custom_after_update=None,
        upsert=False,
        function_name=None,
        retrieve_after_update=False,
        custom_json_response=False,
        retrieve_fields=None,
    ):
        return self.payload

    def partial_update(
        self,
        dto,
        id,
        aditional_filters=None,
        custom_before_update=None,
        custom_after_update=None,
        retrieve_after_partial_update=False,
        custom_json_response=False,
        retrieve_fields=None,
    ):
        return self.payload

    def delete(
        self,
        id,
        additional_filters=None,
        custom_before_delete=None,
        function_params=None,
        function_object=None,
        function_name=None,
        custom_json_response=False,
    ):
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


def _assert_response(result, payload):
    body, status, _ = result
    assert status == 200
    assert json.loads(body) == payload


def test_post_route_custom_json_response():
    payload = {"ok": True}
    service = ResponseService(payload)

    class PostRouteUnderTest(PostRoute):
        def _get_service(self, factory):
            return service

    route = PostRouteUnderTest(
        url="/samples",
        http_method="POST",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        custom_json_response=True,
        insert_function_name="fn_insert",
    )

    with application.test_request_context(
        "/samples", method="POST", json={"id": 1, "name": "foo"}
    ):
        result = route.handle_request()

    _assert_response(result, payload)


def test_put_route_custom_json_response():
    payload = {"updated": True}
    service = ResponseService(payload)

    class PutRouteUnderTest(PutRoute):
        def _get_service(self, factory):
            return service

    route = PutRouteUnderTest(
        url="/samples/<id>",
        http_method="PUT",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        custom_json_response=True,
        update_function_name="fn_update",
    )

    with application.test_request_context(
        "/samples/1", method="PUT", json={"id": 1, "name": "bar"}
    ):
        result = route.handle_request(id="1")

    _assert_response(result, payload)


def test_patch_route_custom_json_response():
    payload = {"patched": True}
    service = ResponseService(payload)

    class PatchRouteUnderTest(PatchRoute):
        def _get_service(self, factory):
            return service

    route = PatchRouteUnderTest(
        url="/samples/<id>",
        http_method="PATCH",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        custom_json_response=True,
    )

    with application.test_request_context(
        "/samples/1", method="PATCH", json={"name": "baz"}
    ):
        result = route.handle_request(id="1")

    _assert_response(result, payload)


def test_delete_route_custom_json_response():
    payload = {"deleted": True}
    service = ResponseService(payload)

    class DeleteRouteUnderTest(DeleteRoute):
        def _get_service(self, factory):
            return service

    route = DeleteRouteUnderTest(
        url="/samples/<id>",
        http_method="DELETE",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        custom_json_response=True,
        delete_function_name="fn_delete",
    )

    with application.test_request_context("/samples/1", method="DELETE"):
        result = route.handle_request(id="1")

    _assert_response(result, payload)
