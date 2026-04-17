import pytest

from rest_lib.decorator.dto import DTO
from rest_lib.descriptor.dto_field import DTOField
from rest_lib.dto.dto_base import DTOBase


@DTO()
class EtagDTO(DTOBase):
    id: int = DTOField(pk=True, resume=True)
    version: str = DTOField()


def test_etag_fields_default_to_resume_fields():
    assert EtagDTO.etag_fields == {"id"}


def test_etag_fields_can_extend_resume_fields():
    @DTO(etag_fields={"version"})
    class CustomEtagDTO(DTOBase):
        id: int = DTOField(pk=True, resume=True)
        version: str = DTOField()

    assert CustomEtagDTO.etag_fields == {"id", "version"}


def test_etag_fields_can_be_disabled():
    @DTO(etag_fields=False)
    class DisabledEtagDTO(DTOBase):
        id: int = DTOField(pk=True, resume=True)
        version: str = DTOField()

    assert DisabledEtagDTO.etag_fields == set()


def test_etag_date_requires_single_field():
    with pytest.raises(AssertionError, match="etag_fields"):

        @DTO(etag_fields={"updated_at", "version"}, etag_type="DATE")
        class InvalidEtagDTO(DTOBase):
            id: int = DTOField(pk=True, resume=True)
            updated_at: str = DTOField()
            version: str = DTOField()
