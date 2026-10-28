from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errores import ApiError
from app.models import Pedido, Usuario
from app.models.enums import Accion, EstadoPedido, Rol
from app.schemas.comun import IdNombre, IdNombreExtra
from app.schemas.pedido import (EntregaOut, ItemCreado, ItemEstado, ItemResumen,
                                PedidoCreado, PedidoEstadoOut, PedidoIn,
                                PedidoListado, PedidosOut)
from app.seguridad import requiere_rol
from app.services import pedido_service
from app.tiempo import parsear_fecha

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


# ---------------------------------------------------------------- cliente
@router.post("", response_model=PedidoCreado, status_code=201, tags=["Cliente (público)"])
def crear_pedido(datos: PedidoIn, db: Session = Depends(get_db)):
    pedido = pedido_service.crear_pedido(db, datos)
    items = []
    for d in pedido.detalles:
        items.append(ItemCreado(
            item_id=d.id, producto_id=d.producto_id, nombre=d.producto.nombre,
            cantidad=d.cantidad, precio_unitario=d.precio_unitario,
            ingredientes_quitados=[IdNombre(id=p.ingrediente_id, nombre=p.ingrediente.nombre)
                                   for p in d.personalizaciones if p.accion == Accion.quitado],
            ingredientes_agregados=[IdNombreExtra(id=p.ingrediente_id, nombre=p.ingrediente.nombre,
                                                  precio_extra=p.precio_extra)
                                    for p in d.personalizaciones if p.accion == Accion.agregado],
        ))
    return PedidoCreado(id=pedido.id, nombre_cliente=pedido.nombre_cliente, estado=pedido.estado,
                        total=pedido.total, fecha_creacion=pedido.fecha_creacion, items=items)


@router.get("/{pedido_id}/estado", response_model=PedidoEstadoOut, tags=["Cliente (público)"])
def estado_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = pedido_service.obtener_pedido(db, pedido_id)
    return PedidoEstadoOut(
        id=pedido.id, nombre_cliente=pedido.nombre_cliente, estado=pedido.estado, total=pedido.total,
        items=[ItemEstado(nombre=d.producto.nombre, cantidad=d.cantidad, estado_cocina=d.estado_cocina)
               for d in pedido.detalles],
    )


# ---------------------------------------------------------------- recepcionista
@router.get("", response_model=PedidosOut, tags=["Recepcionista"])
def listar_pedidos(
    estado: str = "listo",
    fecha: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.recepcionista)),
):
    """estado: listo | entregado | listo,entregado (por defecto listo). fecha: YYYY-MM-DD (por defecto hoy)."""
    validos = {EstadoPedido.listo.value, EstadoPedido.entregado.value}
    partes = [p.strip() for p in estado.split(",")]
    if not partes or any(p not in validos for p in partes):
        raise ApiError(400, "ESTADO_INVALIDO", "estado debe ser 'listo', 'entregado' o 'listo,entregado'")
    dia = parsear_fecha(fecha)

    pedidos = pedido_service.listar_pedidos(db, [EstadoPedido(p) for p in set(partes)], dia)
    return PedidosOut(pedidos=[
        PedidoListado(
            id=p.id, nombre_cliente=p.nombre_cliente, estado=p.estado, total=p.total,
            fecha_creacion=p.fecha_creacion, fecha_listo=p.fecha_listo, fecha_entrega=p.fecha_entrega,
            items=[ItemResumen(nombre=d.producto.nombre, cantidad=d.cantidad) for d in p.detalles],
        ) for p in pedidos
    ])


@router.patch("/{pedido_id}/entregar", response_model=EntregaOut, tags=["Recepcionista"])
def entregar(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(Rol.recepcionista)),
):
    pedido = pedido_service.entregar_pedido(db, pedido_id, usuario)
    return EntregaOut(id=pedido.id, estado=pedido.estado, fecha_entrega=pedido.fecha_entrega)
