import enum


class FilterOperator(enum.Enum):
    EQUALS = "equals"
    DIFFERENT = "diferent"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL_THAN = "greater_or_equal_than"
    LESS_OR_EQUAL_THAN = "less_or_equal_than"
    LIKE = "like"
    ILIKE = "ilike"
    NOT_LIKE = "not_like"
    NOT_ILIKE = "not_ilike"
    NOT_NULL = "not_null"
    LENGTH_GREATER_OR_EQUAL_THAN = "length_greater_or_equal_than"
    LENGTH_LESS_OR_EQUAL_THAN = "length_less_or_equal_than"
    IN = "in"
    NULL = "null"
