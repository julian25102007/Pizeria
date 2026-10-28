from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Accion, EstadoCocina, EstadoPedido, columna_enum
from app.models.producto import Ingrediente, Producto
from app.models.usuario import Usuario
from app.tiempo import ahora


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)  # también es el número de pedido
    nombre_cliente: Mapped[str] = mapped_column(String(80))
    estado: Mapped[EstadoPedido] = mapped_column(
        columna_enum(EstadoPedido), default=EstadoPedido.pendiente
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fecha_creacion: Mapped[datetime] = mapped_column(default=ahora)
    fecha_listo: Mapped[datetime | None] = mapped_column()
    fecha_entrega: Mapped[datetime | None] = mapped_column()
    entregado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    detalles: Mapped[list["DetallePedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan",
        order_by="DetallePedido.id",
    )
    entregador: Mapped[Usuario | None] = relationship()


class DetallePedido(Base):
    """Tabla pedido_items: una pizza personalizada = una fila (cantidad 1)."""

    __tablename__ = "pedido_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[int] = mapped_column(default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    estado_cocina: Mapped[EstadoCocina] = mapped_column(
        columna_enum(EstadoCocina), default=EstadoCocina.pendiente
    )

    pedido: Mapped[Pedido] = relationship(back_populates="detalles")
    producto: Mapped[Producto] = relationship()
    personalizaciones: Mapped[list["Personalizacion"]] = relationship(
        back_populates="detalle", cascade="all, delete-orphan",
        order_by="Personalizacion.id",
    )

    @property
    def producto_nombre(self) -> str:
        return self.producto.nombre


class Personalizacion(Base):
    """Tabla pedido_item_ingredientes: solo los CAMBIOS a la receta base."""

    __tablename__ = "pedido_item_ingredientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("pedido_items.id"))
    ingrediente_id: Mapped[int] = mapped_column(ForeignKey("ingredientes.id"))
    accion: Mapped[Accion] = mapped_column(columna_enum(Accion))
    precio_extra: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)

    detalle: Mapped[DetallePedido] = relationship(back_populates="personalizaciones")
    ingrediente: Mapped[Ingrediente] = relationship()

    @property
    def ingrediente_nombre(self) -> str:
        return self.ingrediente.nombre
