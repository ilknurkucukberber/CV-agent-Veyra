"""Geriye dönük uyumlu, opsiyonel sayfalama yardımcıları.

`limit` verilmezse davranış değişmez (tüm kayıtlar döner) — mevcut frontend
tüketicileri (düz dizi bekleyen) kırılmadan çalışmaya devam eder. `limit`
verildiğinde SQL tarafında LIMIT/OFFSET uygulanır.
"""

from typing import Annotated

from fastapi import Query
from sqlalchemy import Select

OptionalLimit = Annotated[
    int | None, Query(ge=1, le=200, description="Sayfa başına kayıt sayısı")
]
Offset = Annotated[int, Query(ge=0, description="Atlanacak kayıt sayısı")]


def paginate(stmt: Select, limit: int | None, offset: int) -> Select:
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return stmt
