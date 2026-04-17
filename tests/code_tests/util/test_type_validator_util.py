from types import SimpleNamespace

from dateutil.relativedelta import relativedelta

from rest_lib.util.type_validator_util import TypeValidatorUtil


def _duration_field():
    return SimpleNamespace(expected_type=relativedelta, storage_name="carga_horaria")


def test_validate_duration_maps_days_correctly():
    value = TypeValidatorUtil.validate(_duration_field(), "P1D")

    assert value.years == 0
    assert value.months == 0
    assert value.days == 1
    assert value.hours == 0
    assert value.minutes == 0
    assert value.seconds == 0


def test_validate_duration_supports_fractional_seconds():
    value = TypeValidatorUtil.validate(_duration_field(), "PT1.5S")

    assert value.seconds == 1
    assert value.microseconds == 500000
