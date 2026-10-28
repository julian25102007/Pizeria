from decimal import Decimal

from sqlalchemy import true, Column, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TipoProducto, columna_enum

# Receta base de cada pizza (tabla intermedia muchos a muchos)
producto_ingredientes = Table(
    "producto_ingredientes",
    Base.metadata,
    Column("producto_id", Integer, ForeignKey("productos.id"), primary_key=True),
    Column("ingrediente_id", Integer, ForeignKey("ingredientes.id"), primary_key=True),
)


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    precio_extra: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    activo: Mapped[bool] = mapped_column(default=True, server_default=true())


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    tipo: Mapped[TipoProducto] = mapped_column(
        columna_enum(TipoProducto), default=TipoProducto.pizza
    )
    precio: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    imagen_url: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(default=True, server_default=true())

    ingredientes: Mapped[list[Ingrediente]] = relationship(
        secondary=producto_ingredientes
    )
