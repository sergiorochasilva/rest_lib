import uuid
import typing as ty

from rest_lib.decorator.dto import DTO  # type: ignore
from rest_lib.descriptor.dto_field import DTOField  # type: ignore
from rest_lib.descriptor.dto_list_field import DTOListField  # type: ignore
from rest_lib.descriptor.dto_one_to_one_field import (  # type: ignore
    DTOOneToOneField,
    OTORelationType,
)
from rest_lib.descriptor.dto_left_join_field import EntityRelationOwner  # type: ignore

from rest_lib.dto.dto_base import DTOBase  # type: ignore

from rest_lib.decorator.entity import Entity  # type: ignore
from rest_lib.entity.entity_base import EntityBase  # type: ignore

from rest_lib.dao.dao_base import DAOBase  # type: ignore
from rest_lib.exception import NotFoundException  # type: ignore
from rest_lib.service.service_base import ServiceBase  # type: ignore


@Entity(table_name="child_entity", pk_field="a", default_order_fields=["a"])
class ChildEntity(EntityBase):
    a: uuid.UUID = uuid.UUID(int=0)
    pass


@DTO()
class ChildDTO(DTOBase):
    a: int = DTOField(pk=True, resume=True)
    pass


@Entity(table_name="parent_entity", pk_field="b", default_order_fields=["b"])
class ParentEntity(EntityBase):
    b: uuid.UUID = uuid.UUID(int=0)
    child: uuid.UUID = uuid.UUID(int=0)
    pass


@DTO()
class ParentDTO(DTOBase):
    b: int = DTOField(pk=True, resume=True)
    child: ChildDTO = DTOOneToOneField(
        not_null=True,
        entity_type=ChildEntity,
        relation_type=OTORelationType.AGGREGATION,
    )
    pass


@Entity(table_name="child_code_entity", pk_field="id", default_order_fields=["id"])
class ChildCodeEntity(EntityBase):
    id: uuid.UUID = uuid.UUID(int=0)
    code: str = ""
    pass


@DTO()
class ChildCodeDTO(DTOBase):
    id: int = DTOField(pk=True, resume=True)
    code: str = DTOField()
    pass


@Entity(table_name="parent_code_entity", pk_field="pid", default_order_fields=["pid"])
class ParentCodeEntity(EntityBase):
    pid: uuid.UUID = uuid.UUID(int=0)
    child: str = ""
    pass


@DTO()
class ParentCodeDTO(DTOBase):
    pid: int = DTOField(pk=True, resume=True)
    child: ChildCodeDTO = DTOOneToOneField(
        entity_type=ChildCodeEntity,
        relation_type=OTORelationType.AGGREGATION,
        relation_field="code",
    )
    pass


class ParentDAO(DAOBase):
    def __init__(self, da, entity_class):
        super().__init__(db=da, entity_class=entity_class)
        self.count = 10
        pass

    # pylint: disable-next=arguments-differ
    def insert(self, entity: EntityBase, *_, **__):
        return entity

    def begin(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    # pylint: disable-next=arguments-differ
    def get(self, *_, **__) -> EntityBase:
        raise NotFoundException("")

    # pylint: disable-next=arguments-differ
    def entity_exists(self, *_, **__):
        return False

    pass


@Entity(table_name="detail_entity", pk_field="detail_id", default_order_fields=["detail_id"])
class DetailEntity(EntityBase):
    detail_id: uuid.UUID = uuid.UUID(int=0)
    pass


@DTO()
class DetailDTO(DTOBase):
    detail_id: int = DTOField(pk=True, resume=True)
    pass


@Entity(table_name="list_item_entity", pk_field="item_id", default_order_fields=["item_id"])
class ListItemEntity(EntityBase):
    item_id: uuid.UUID = uuid.UUID(int=0)
    detail: uuid.UUID = uuid.UUID(int=0)
    pass


@DTO()
class ListItemDTO(DTOBase):
    item_id: int = DTOField(pk=True, resume=True)
    detail: DetailDTO = DTOOneToOneField(
        entity_type=DetailEntity,
        relation_type=OTORelationType.COMPOSITION,
    )
    pass


@DTO()
class ParentWithListDTO(DTOBase):
    id: int = DTOField(pk=True, resume=True)
    items: ty.List[ListItemDTO] = DTOListField(
        dto_type=ListItemDTO,
        entity_type=ListItemEntity,
        related_entity_field="parent_id",
    )
    pass


def test_configure() -> None:
    oto_field: DTOOneToOneField = ParentDTO.one_to_one_fields_map["child"]
    field: DTOField = ParentDTO.fields_map["child"]

    assert oto_field.field is field
    assert oto_field.expected_type is ChildDTO
    pass


def test_insert_uuid() -> None:
    vals: ty.Dict[str, ty.Any] = {"child": {"a": uuid.UUID(int=0xDEADBEEF)}}
    dto = ParentDTO(**vals)
    service = ServiceBase(
        injector_factory=None,
        dao=ParentDAO(da=None, entity_class=ParentEntity),
        dto_class=ParentDTO,
        entity_class=ParentEntity,
        dto_post_response_class=ParentDTO,
    )
    dto_response: ParentDTO = service.insert(dto)
    assert dto_response.child == vals["child"]["a"]
    pass


def test_insert_object() -> None:
    vals: ty.Dict[str, ty.Any] = {"child": uuid.UUID(int=0xDEADBEEF)}
    dto = ParentDTO(**vals)
    service = ServiceBase(
        injector_factory=None,
        dao=ParentDAO(da=None, entity_class=ParentEntity),
        dto_class=ParentDTO,
        entity_class=ParentEntity,
        dto_post_response_class=ParentDTO,
    )
    dto_response: ParentDTO = service.insert(dto)
    assert dto_response.child == vals["child"]
    pass


def test_relation_field_aggregation_uses_custom_field() -> None:
    child = ChildCodeDTO(id=1, code="A1")
    dto = ParentCodeDTO(child=child)
    assert dto.child == "A1"

    dto_from_dict = ParentCodeDTO(child={"code": "B2"})
    assert dto_from_dict.child == "B2"
    pass


def test_invalid_entity_type() -> None:
    exp_msg: str = (
        "Argument `entity_type` of `DTOOneToOneField` HAS to be a"
        " `EntityBase`. Is <class 'object'>."
    )
    try:

        @DTO()
        class _DTO(DTOBase):
            child: ChildDTO = DTOOneToOneField(
                entity_type=object,
                relation_type=OTORelationType.AGGREGATION,
            )
            pass

    except AssertionError as err:
        if err.args[0] != exp_msg:
            raise err
        pass
    pass


def test_no_annotation() -> None:
    exp_msg: str = "`DTOOneToOneField` with name `child` HAS to have an" " annotation."
    try:

        @DTO()
        class _DTO(DTOBase):
            child = DTOOneToOneField(
                entity_type=ChildEntity,
                relation_type=OTORelationType.AGGREGATION,
            )
            pass

    except AssertionError as err:
        if err.args[0] != exp_msg:
            raise err
        pass
    pass


def test_invalid_expected_type() -> None:
    exp_msg: str = (
        "`DTOOneToOneField` with name `child` annotation's MUST"
        " be a subclass of `DTOBase`. Is `<class 'object'>`."
    )
    try:

        @DTO()
        class _DTO(DTOBase):
            child: object = DTOOneToOneField(
                entity_type=ChildEntity,
                relation_type=OTORelationType.AGGREGATION,
            )
            pass

    except AssertionError as err:
        if err.args[0] != exp_msg:
            raise err
        pass
    pass


def test_entity_relation_owner_other() -> None:
    exp_msg: str = "At the moment only `EntityRelationOwner.SELF` is supported."
    try:

        @DTO()
        class _DTO(DTOBase):
            child: ChildDTO = DTOOneToOneField(
                entity_type=ChildEntity,
                relation_type=OTORelationType.AGGREGATION,
                entity_relation_owner=EntityRelationOwner.OTHER,
            )
            pass

    except AssertionError as err:
        if err.args[0] != exp_msg:
            raise err
        pass
    pass


def test_list_fields_propagate_one_to_one_expands() -> None:
    detail_dto = DetailDTO(detail_id=42)
    list_item_dto = ListItemDTO(item_id=7, detail=detail_dto)
    parent = ParentWithListDTO(id=99, items=[list_item_dto])

    fields = {
        "root": {"items"},
        "items": {
            "root": {"item_id", "detail"},
            "detail": {"root": {"detail_id"}},
        },
    }
    expands = {"root": {"items"}, "items": {"root": {"detail"}}}

    dto_dict = parent.convert_to_dict(fields, expands)

    assert "items" in dto_dict
    assert dto_dict["items"][0]["detail"] == {"detail_id": detail_dto.detail_id}
