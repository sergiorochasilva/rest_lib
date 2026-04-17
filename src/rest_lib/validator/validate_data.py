import re


def validate_uuid(value: str) -> bool:
    """
    Validate a UUID or UUID in string
    """
    value = str(value)

    if len(value) != 36:
        return False

    pattern = '^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$'
    return re.search(pattern, value) is not None


def validate_email(value: str) -> bool:
    """
    Validate a email in string
    """
    value = str(value)

    pattern = '^[^@\n]+@[^@\n]+(\.[^@\n]+)+$'
    return re.search(pattern, value) is not None
