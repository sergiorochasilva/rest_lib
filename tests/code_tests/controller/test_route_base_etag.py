import sys
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rest_lib.controller.route_base import RouteBase


def test_parse_if_none_match_multiple_values():
    header = '"one" , "two" , "three"'

    assert RouteBase.parse_if_none_match(header) == ["one", "two", "three"]


def test_parse_if_none_match_supports_escapes():
    header = '"a\\"b", "c"'

    assert RouteBase.parse_if_none_match(header) == ['a"b', "c"]


def test_parse_if_none_match_ignores_unterminated_values():
    header = '"unterminated'

    assert RouteBase.parse_if_none_match(header) == []


def test_parse_if_none_match_accepts_weak_etags():
    header = 'W/"weak", "strong"'

    assert RouteBase.parse_if_none_match(header) == ["weak", "strong"]


def test_quote_and_escape_string_wraps_and_escapes():
    assert RouteBase.quote_and_escape_string('a"b') == '"a\\"b"'
    assert RouteBase.quote_and_escape_string("plain") == '"plain"'
    assert RouteBase.quote_and_escape_string("") == '""'


def test_get_etag_value_raw_type():
    class DummyDTO:
        etag_fields = {"version"}
        etag_type = "RAW"

        def __init__(self, version):
            self.version = version

    assert RouteBase.get_etag_value(DummyDTO("v1")) == "v1"


def test_get_etag_value_hash_type():
    class DummyDTO:
        etag_fields = {"version"}
        etag_type = "HASH"

        def __init__(self, version):
            self.version = version

    expected = hashlib.sha256("v1".encode("utf-8")).hexdigest()
    assert RouteBase.get_etag_value(DummyDTO("v1")) == expected


def test_is_etag_value_in_list_date_type():
    assert RouteBase.is_etag_value_in_list(
        "DATE",
        "2024-01-02T00:00:00",
        ["2024-01-01T00:00:00"],
    )
    assert not RouteBase.is_etag_value_in_list(
        "DATE",
        "2024-01-01T00:00:00",
        ["2024-01-02T00:00:00"],
    )


def test_is_etag_value_in_list_raw_and_hash_types():
    assert RouteBase.is_etag_value_in_list("RAW", "abc", ["abc"])
    assert RouteBase.is_etag_value_in_list("HASH", "abc", ["abc"])
    assert not RouteBase.is_etag_value_in_list("HASH", "abc", ["def"])
