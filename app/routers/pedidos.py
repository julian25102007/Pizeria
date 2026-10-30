from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errores import ApiError
from app.models import Pedido, Usuario
from app.models.enums import Accion, EstadoPedido, Rol
from app.schemas.comun import IdNombre, IdNombreExtra
from app.schemas.pedido import (CobroOut, EntregaOut, ItemCreado, ItemEstado, ItemResumen,
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
        fecha_creacion=pedido.fecha_creacion, fecha_listo=pedido.fecha_listo, pagado=pedido.pagado,
        espera_estimada_min=pedido_service.espera_estimada_min(db, pedido),
    )


# ---------------------------------------------------------------- recepcionista
def _listado(p: Pedido) -> PedidoListado:
    return PedidoListado(
        id=p.id, nombre_cliente=p.nombre_cliente, estado=p.estado, total=p.total,
        fecha_creacion=p.fecha_creacion, fecha_listo=p.fecha_listo, fecha_entrega=p.fecha_entrega,
        items=[ItemResumen(nombre=d.producto.nombre, cantidad=d.cantidad) for d in p.detalles],
        pagado=p.pagado, fecha_pago=p.fecha_pago,
    )


@router.get("", response_model=PedidosOut, tags=["Recepcionista"])
def listar_pedidos(
    estado: str = "listo",
    fecha: str | None = None,
    pagado: bool | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.recepcionista, Rol.administrador)),
):
    """estado: listo | entregado | listo,entregado (por defecto listo). fecha: YYYY-MM-DD (por defecto hoy).
    pagado: true | false para filtrar por cobro (opcional)."""
    validos = {EstadoPedido.listo.value, EstadoPedido.entregado.value}
    partes = [p.strip() for p in estado.split(",")]
    if not partes or any(p not in validos for p in partes):
        raise ApiError(400, "ESTADO_INVALIDO", "estado debe ser 'listo', 'entregado' o 'listo,entregado'")
    dia = parsear_fecha(fecha)

    pedidos = pedido_service.listar_pedidos(db, [EstadoPedido(p) for p in set(partes)], dia, pagado)
    return PedidosOut(pedidos=[_listado(p) for p in pedidos])


@router.get("/pendientes", response_model=PedidosOut, tags=["Recepcionista"])
def pedidos_pendientes(
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.recepcionista, Rol.administrador)),
):
    """Pedidos que cocina todavía está preparando (cola de recepción)."""
    return PedidosOut(pedidos=[_listado(p) for p in pedido_service.pedidos_pendientes(db)])


@router.patch("/{pedido_id}/cobrar", response_model=CobroOut, tags=["Recepcionista"])
def cobrar(
    pedido_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(requiere_rol(Rol.recepcionista)),
):
    """Registra el cobro del pedido. Es independiente de cocina y de la entrega."""
    p = pedido_service.cobrar_pedido(db, pedido_id)
    return CobroOut(id=p.id, total=p.total, pagado=p.pagado, fecha_pago=p.fecha_pago)


@router.patch("/{pedido_id}/entregar", response_model=EntregaOut, tags=["Recepcionista"])
def entregar(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(requiere_rol(Rol.recepcionista)),
):
    pedido = pedido_service.entregar_pedido(db, pedido_id, usuario)
    return EntregaOut(id=pedido.id, estado=pedido.estado, fecha_entrega=pedido.fecha_entrega)
