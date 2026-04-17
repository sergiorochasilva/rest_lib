from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderFieldSource(Enum):
    BASE = "base"
    PARTIAL_EXTENSION = "partial_extension"


@dataclass(frozen=True)
class OrderFieldSpec:
    column: str
    is_desc: bool = False
    source: OrderFieldSource = OrderFieldSource.BASE
    alias: str | None = None


PARTIAL_JOIN_ALIAS = "partial_join"
