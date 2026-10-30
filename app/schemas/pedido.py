from datetime import datetime

from pydantic import BaseModel

from app.models.enums import EstadoCocina, EstadoPedido
from app.schemas.comun import Dinero, IdNombre, IdNombreExtra


# ---------- POST /pedidos (entrada) ----------
# Las reglas de negocio (nombre, items vacíos, cantidades...) se validan en el
# servicio para devolver 422 con el código del contrato.
class ItemIn(BaseModel):
    producto_id: int
    cantidad: int = 1
    ingredientes_quitar: list[int] = []
    ingredientes_agregar: list[int] = []


class PedidoIn(BaseModel):
    nombre_cliente: str | None = None
    items: list[ItemIn] = []


# ---------- POST /pedidos (respuesta 201) ----------
class ItemCreado(BaseModel):
    item_id: int
    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: Dinero
    ingredientes_quitados: list[IdNombre]
    ingredientes_agregados: list[IdNombreExtra]


class PedidoCreado(BaseModel):
    id: int
    nombre_cliente: str
    estado: EstadoPedido
    total: Dinero
    fecha_creacion: datetime
    items: list[ItemCreado]


# ---------- GET /pedidos/{id}/estado ----------
class ItemEstado(BaseModel):
    nombre: str
    cantidad: int
    estado_cocina: EstadoCocina


class PedidoEstadoOut(BaseModel):
    id: int
    nombre_cliente: str
    estado: EstadoPedido
    total: Dinero
    items: list[ItemEstado]
    fecha_creacion: datetime
    fecha_listo: datetime | None = None
    pagado: bool = False
    espera_estimada_min: int = 0  # 0 si el pedido ya está listo o entregado


# ---------- cocina ----------
class ItemCola(BaseModel):
    item_id: int
    pedido_id: int
    nombre_cliente: str
    pizza: str
    fecha_creacion: datetime
    ingredientes: list[IdNombre]  # receta base - quitados + agregados
    quitados: list[IdNombre]
    agregados: list[IdNombre]


class ColaOut(BaseModel):
    cola: list[ItemCola]


class ItemListaOut(BaseModel):
    item_id: int
    estado_cocina: EstadoCocina
    pedido_id: int
    pedido_estado: EstadoPedido


# ---------- recepcionista ----------
class ItemResumen(BaseModel):
    nombre: str
    cantidad: int


class PedidoListado(BaseModel):
    id: int
    nombre_cliente: str
    estado: EstadoPedido
    total: Dinero
    fecha_creacion: datetime
    fecha_listo: datetime | None
    fecha_entrega: datetime | None
    items: list[ItemResumen]
    pagado: bool = False
    fecha_pago: datetime | None = None


class PedidosOut(BaseModel):
    pedidos: list[PedidoListado]


class EntregaOut(BaseModel):
    id: int
    estado: EstadoPedido
    fecha_entrega: datetime

class HistorialPedidosOut(BaseModel):
    total: int
    pedidos: list[PedidoListado]


class CobroOut(BaseModel):
    id: int
    total: Dinero
    pagado: bool
    fecha_pago: datetime
