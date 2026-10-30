from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


Dinero = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class IdNombre(BaseModel):
    id: int
    nombre: str


class IdNombreExtra(BaseModel):
    id: int
    nombre: str
    precio_extra: Dinero
