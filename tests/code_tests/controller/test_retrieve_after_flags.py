import typing as ty
from pathlib import Path
import sys

# Garantindo import da lib local sem depender de instalação no ambiente
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rest_lib.controller.patch_route import PatchRoute
from rest_lib.controller.post_route import PostRoute
from rest_lib.controller.put_route import PutRoute
from rest_lib.decorator.dto import DTO
from rest_lib.decorator.entity import Entity
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.descriptor.function_field import FunctionField
from rest_lib.decorator.insert_function_type import InsertFunctionType
from rest_lib.decorator.update_function_type import UpdateFunctionType
from rest_lib.descriptor.entity_field import EntityField
from rest_lib.dto.dto_base import DTOBase
from rest_lib.entity.entity_base import EntityBase
from rest_lib.entity.function_type_base import (
    InsertFunctionTypeBase,
    UpdateFunctionTypeBase,
)
from rest_lib.service.service_base import ServiceBase
from rest_lib.settings import application


class FakeInjectorFactory:
    """
    Minimal injector factory that behaves as a context manager but does nothing.
    """

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class DummyResponse:
    def __init__(self, payload: ty.Optional[dict] = None):
        self._payload = payload or {"ok": True}

    def convert_to_dict(self):
        return self._payload


class RecordingRouteService:
    def __init__(self):
        self.called_with: dict[str, ty.Any] | None = None

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
        self.called_with = {"retrieve_after_insert": retrieve_after_insert, "dto": dto}
        return DummyResponse()

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
        self.called_with = {"retrieve_after_update": retrieve_after_update, "dto": dto, "id": id}
        return DummyResponse()

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
        self.called_with = {
            "retrieve_after_partial_update": retrieve_after_partial_update,
            "dto": dto,
            "id": id,
        }
        return DummyResponse()


@DTO()
class SampleDTO(DTOBase):
    id: int = DTOField(pk=True)
    name: str = DTOField()
    auto_increment_fields = {}


@Entity(table_name="public.sample", pk_field="id", default_order_fields=["id"])
class SampleEntity(EntityBase):
    id: int = EntityField()
    name: str = EntityField()


@InsertFunctionType(type_name="public.fn_sample_ins")
class SampleInsertFunction(InsertFunctionTypeBase):
    id: int = FunctionField()
    name: str = FunctionField()


@UpdateFunctionType(type_name="public.fn_sample_upd")
class SampleUpdateFunction(UpdateFunctionTypeBase):
    id: int = FunctionField()
    name: str = FunctionField()


class FakeDAO:
    def __init__(self):
        self._db = None
        self.insert_by_function_called = None
        self.update_by_function_called = None

    def begin(self):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def insert(self, entity, sql_read_only_fields):
        return entity

    def insert_by_function(self, func_object, function_name=None, custom_json_response=False):
        self.insert_by_function_called = (func_object, function_name)
        return None

    def update(
        self,
        pk_field,
        pk_value,
        entity,
        aditional_entity_filters,
        partial_update,
        sql_read_only_fields,
        sql_no_update_fields,
        upsert,
    ):
        return entity

    def update_by_function(self, func_object, function_name=None, custom_json_response=False):
        self.update_by_function_called = (func_object, function_name)
        return None


class FakeInjector:
    def db_adapter(self):
        return None


class FunctionRecordingService(ServiceBase):
    def __init__(
        self,
        dao: FakeDAO,
        insert_function_type_class=None,
        update_function_type_class=None,
    ):
        super().__init__(
            injector_factory=FakeInjector(),
            dao=dao,
            dto_class=SampleDTO,
            entity_class=SampleEntity,
            insert_function_type_class=insert_function_type_class,
            update_function_type_class=update_function_type_class,
        )
        self.get_calls: list[tuple] = []

    def entity_exists(self, *args, **kwargs):
        return False

    def _check_unique(self, *args, **kwargs):
        return None

    def _retrieve_old_dto(self, dto, id, aditional_filters):
        # Avoids hitting DAO during tests
        return dto

    def get(self, id, aditional_filters=None, fields=None):
        self.get_calls.append((id, aditional_filters, fields))
        return SampleDTO(id=id, name="retrieved", escape_validator=True)


def test_post_route_propagates_retrieve_after_insert_flag():
    service = RecordingRouteService()

    class PostRouteUnderTest(PostRoute):
        def _get_service(self, factory):
            return service

    route = PostRouteUnderTest(
        url="/samples",
        http_method="POST",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        retrieve_after_insert=True,
    )

    with application.test_request_context("/samples", method="POST", json={"id": 1, "name": "foo"}):
        route.handle_request()

    assert service.called_with is not None
    assert service.called_with["retrieve_after_insert"] is True


def test_put_route_propagates_retrieve_after_update_flag():
    service = RecordingRouteService()

    class PutRouteUnderTest(PutRoute):
        def _get_service(self, factory):
            return service

    route = PutRouteUnderTest(
        url="/samples/<id>",
        http_method="PUT",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        retrieve_after_update=True,
    )

    with application.test_request_context("/samples/1", method="PUT", json={"id": 1, "name": "bar"}):
        route.handle_request(id="1")

    assert service.called_with is not None
    assert service.called_with["retrieve_after_update"] is True


def test_patch_route_propagates_retrieve_after_partial_update_flag():
    service = RecordingRouteService()

    class PatchRouteUnderTest(PatchRoute):
        def _get_service(self, factory):
            return service

    route = PatchRouteUnderTest(
        url="/samples/<id>",
        http_method="PATCH",
        dto_class=SampleDTO,
        entity_class=SampleEntity,
        injector_factory=FakeInjectorFactory,
        retrieve_after_partial_update=True,
    )

    with application.test_request_context("/samples/1", method="PATCH", json={"name": "baz"}):
        route.handle_request(id="1")

    assert service.called_with is not None
    assert service.called_with["retrieve_after_partial_update"] is True


def test_insert_by_function_triggers_retrieve():
    dao = FakeDAO()
    service = FunctionRecordingService(
        dao=dao,
        insert_function_type_class=SampleInsertFunction,
    )

    dto = SampleDTO(id=10, name="foo")

    with application.app_context():
        response = service.insert(dto, retrieve_after_insert=True, function_name="fn_insert")

    assert dao.insert_by_function_called is not None
    assert service.get_calls and service.get_calls[-1][0] == 10
    assert isinstance(response, SampleDTO)


def test_update_by_function_triggers_retrieve():
    dao = FakeDAO()
    service = FunctionRecordingService(
        dao=dao,
        update_function_type_class=SampleUpdateFunction,
    )

    dto = SampleDTO(id=20, name="bar")

    with application.app_context():
        response = service.update(
            dto,
            id=20,
            retrieve_after_update=True,
            function_name="fn_update",
        )

    assert dao.update_by_function_called is not None
    assert service.get_calls and service.get_calls[-1][0] == 20
    assert isinstance(response, SampleDTO)


def test_partial_update_by_function_triggers_retrieve():
    dao = FakeDAO()
    service = FunctionRecordingService(
        dao=dao,
        update_function_type_class=SampleUpdateFunction,
    )

    dto = SampleDTO(id=30, name="baz")

    with application.app_context():
        response = service.partial_update(
            dto,
            id=30,
            retrieve_after_partial_update=True,
        )

    assert dao.update_by_function_called is not None
    assert service.get_calls and service.get_calls[-1][0] == 30
    assert isinstance(response, SampleDTO)
