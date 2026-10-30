from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import TipoProducto, TipoReferencia
from app.schemas.comun import Dinero



class PrecioProductoIn(BaseModel):
    precio: Decimal


class PrecioIngredienteIn(BaseModel):
    precio_extra: Decimal


class CambioPrecioOut(BaseModel):
    id: int
    nombre: str
    precio_anterior: Dinero
    precio_nuevo: Dinero


class CambioHistorial(BaseModel):
    id: int
    tipo: TipoReferencia
    referencia_id: int
    nombre: str | None
    precio_anterior: Dinero
    precio_nuevo: Dinero
    usuario: str
    fecha: datetime


class HistorialOut(BaseModel):
    cambios: list[CambioHistorial]


class VentasDia(BaseModel):
    num_pedidos: int
    total_ventas: Dinero


class ProductoMasVendido(BaseModel):
    id: int
    nombre: str
    unidades: int


class EstadisticasOut(BaseModel):
    fecha: str
    ventas_dia: VentasDia
    producto_mas_vendido: ProductoMasVendido | None

class ProductoIn(BaseModel):
    nombre: str
    descripcion: str | None = None
    tipo: TipoProducto = TipoProducto.pizza
    precio: Decimal
    imagen_url: str | None = None
    ingredientes_base: list[int] = []


class IngredienteIn(BaseModel):
    nombre: str
    precio_extra: Decimal = Decimal("0")


class EliminadoOut(BaseModel):
    id: int
    nombre: str
    activo: bool