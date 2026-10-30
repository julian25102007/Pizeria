from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import TipoReferencia, columna_enum
from app.tiempo import ahora


class HistorialPrecio(Base):
    __tablename__ = "historial_precios"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoReferencia] = mapped_column(columna_enum(TipoReferencia))
    referencia_id: Mapped[int] = mapped_column()
    precio_anterior: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    precio_nuevo: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    fecha: Mapped[datetime] = mapped_column(default=ahora)
