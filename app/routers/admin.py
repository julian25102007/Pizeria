from datetime import date, timedelta

from sqlalchemy import func, select
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.errores import ApiError
from app.models import HistorialPrecio, Ingrediente, Producto, Usuario
from app.models.enums import EstadoPedido, Rol, TipoReferencia
from app.schemas.admin import (CambioHistorial, CambioPrecioOut, EliminadoOut, EstadisticasOut,
                               HistorialOut, IngredienteIn, PedidosPorEstadoOut,
                               PrecioIngredienteIn, PrecioProductoIn, ProductoIn,
                               ProductosVendidosOut, VentasPorDiaOut, VentasPorHoraOut)
from app.schemas.comun import IdNombre, IdNombreExtra
from app.schemas.pedido import HistorialPedidosOut, ItemResumen, PedidoListado
from app.schemas.producto import ProductoDetalle
from app.seguridad import requiere_rol
from app.services import (catalogo_service, estadisticas_service, pedido_service,
                          precio_service)
from app.tiempo import parsear_fecha

router = APIRouter(prefix="/admin", tags=["Administrador"])
solo_admin = requiere_rol(Rol.administrador)


@router.put("/productos/{producto_id}/precio", response_model=CambioPrecioOut)
def precio_producto(producto_id: int, datos: PrecioProductoIn,
                    db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)):
    return precio_service.cambiar_precio_producto(db, producto_id, datos.precio, admin)


@router.put("/ingredientes/{ingrediente_id}/precio", response_model=CambioPrecioOut)
def precio_ingrediente(ingrediente_id: int, datos: PrecioIngredienteIn,
                       db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)):
    return precio_service.cambiar_precio_ingrediente(db, ingrediente_id, datos.precio_extra, admin)


@router.get("/historial-precios", response_model=HistorialOut)
def historial(tipo: TipoReferencia | None = None,
              db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    """Últimos 50 cambios, del más reciente al más antiguo."""
    consulta = (
        select(HistorialPrecio, Usuario.nombre, func.coalesce(Producto.nombre, Ingrediente.nombre))
        .join(Usuario, Usuario.id == HistorialPrecio.usuario_id)
        .outerjoin(Producto, (HistorialPrecio.tipo == TipoReferencia.producto)
                   & (Producto.id == HistorialPrecio.referencia_id))
        .outerjoin(Ingrediente, (HistorialPrecio.tipo == TipoReferencia.ingrediente)
                   & (Ingrediente.id == HistorialPrecio.referencia_id))
        .order_by(HistorialPrecio.fecha.desc(), HistorialPrecio.id.desc())
        .limit(50)
    )
    if tipo:
        consulta = consulta.where(HistorialPrecio.tipo == tipo)
    return HistorialOut(cambios=[
        CambioHistorial(id=h.id, tipo=h.tipo, referencia_id=h.referencia_id, nombre=nombre,
                        precio_anterior=h.precio_anterior, precio_nuevo=h.precio_nuevo,
                        usuario=usuario, fecha=h.fecha)
        for h, usuario, nombre in db.execute(consulta).all()
    ])


@router.get("/estadisticas", response_model=EstadisticasOut)
def estadisticas(fecha: str | None = None,
                 db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return estadisticas_service.estadisticas_del_dia(db, parsear_fecha(fecha))

@router.post("/productos", response_model=ProductoDetalle, status_code=201)
def crear_producto(datos: ProductoIn, db: Session = Depends(get_db),
                   _: Usuario = Depends(solo_admin)):
    p = catalogo_service.crear_producto(db, datos)
    base = sorted(p.ingredientes, key=lambda i: i.id)
    return ProductoDetalle(id=p.id, nombre=p.nombre, descripcion=p.descripcion, tipo=p.tipo,
                           precio=p.precio, imagen_url=p.imagen_url,
                           ingredientes_base=[IdNombre(id=i.id, nombre=i.nombre) for i in base])


@router.delete("/productos/{producto_id}", response_model=EliminadoOut)
def eliminar_producto(producto_id: int, db: Session = Depends(get_db),
                      _: Usuario = Depends(solo_admin)):
    p = catalogo_service.eliminar_producto(db, producto_id)
    return EliminadoOut(id=p.id, nombre=p.nombre, activo=p.activo)


@router.post("/ingredientes", response_model=IdNombreExtra, status_code=201)
def crear_ingrediente(datos: IngredienteIn, db: Session = Depends(get_db),
                      _: Usuario = Depends(solo_admin)):
    i = catalogo_service.crear_ingrediente(db, datos)
    return IdNombreExtra(id=i.id, nombre=i.nombre, precio_extra=i.precio_extra)


@router.delete("/ingredientes/{ingrediente_id}", response_model=EliminadoOut)
def eliminar_ingrediente(ingrediente_id: int, db: Session = Depends(get_db),
                         _: Usuario = Depends(solo_admin)):
    i = catalogo_service.eliminar_ingrediente(db, ingrediente_id)
    return EliminadoOut(id=i.id, nombre=i.nombre, activo=i.activo)

@router.get("/pedidos", response_model=HistorialPedidosOut)
def historial_pedidos(
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(solo_admin),
):
    """estado: pendiente | listo | entregado (varios separados por coma). Fechas YYYY-MM-DD."""
    estados = []
    if estado:
        try:
            estados = [EstadoPedido(p.strip()) for p in estado.split(",")]
        except ValueError:
            raise ApiError(400, "ESTADO_INVALIDO",
                           "estado debe ser pendiente, listo o entregado (separados por coma)")
    d = parsear_fecha(desde) if desde else None
    h = parsear_fecha(hasta) if hasta else None
    if d and h and d > h:
        raise ApiError(400, "RANGO_INVALIDO", "desde no puede ser mayor que hasta")
    total, pedidos = pedido_service.historial_pedidos(db, estados, d, h, limite, offset)
    return HistorialPedidosOut(total=total, pedidos=[
        PedidoListado(
            id=p.id, nombre_cliente=p.nombre_cliente, estado=p.estado, total=p.total,
            fecha_creacion=p.fecha_creacion, fecha_listo=p.fecha_listo,
            fecha_entrega=p.fecha_entrega,
            items=[ItemResumen(nombre=x.producto.nombre, cantidad=x.cantidad) for x in p.detalles],
            pagado=p.pagado, fecha_pago=p.fecha_pago,
        ) for p in pedidos
    ])


# ---------------------------------------------------------------- datos para gráficas
def _rango(desde: str | None, hasta: str | None) -> tuple[date, date]:
    """Por defecto: los últimos 7 días (incluido hoy). Máximo 366 días."""
    h = parsear_fecha(hasta)
    d = parsear_fecha(desde) if desde else h - timedelta(days=6)
    if d > h:
        raise ApiError(400, "RANGO_INVALIDO", "desde no puede ser mayor que hasta")
    if (h - d).days > 366:
        raise ApiError(400, "RANGO_INVALIDO", "El rango máximo es de 366 días")
    return d, h


@router.get("/estadisticas/ventas-por-dia", response_model=VentasPorDiaOut)
def ventas_por_dia(desde: str | None = None, hasta: str | None = None, solo_pagados: bool = True,
                   db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    d, h = _rango(desde, hasta)
    return VentasPorDiaOut(desde=d.isoformat(), hasta=h.isoformat(), solo_pagados=solo_pagados,
                           dias=estadisticas_service.ventas_por_dia(db, d, h, solo_pagados))


@router.get("/estadisticas/productos-vendidos", response_model=ProductosVendidosOut)
def productos_vendidos(desde: str | None = None, hasta: str | None = None, solo_pagados: bool = True,
                       limite: int = Query(10, ge=1, le=50),
                       db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    d, h = _rango(desde, hasta)
    return ProductosVendidosOut(
        desde=d.isoformat(), hasta=h.isoformat(), solo_pagados=solo_pagados,
        productos=estadisticas_service.productos_vendidos(db, d, h, solo_pagados, limite))


@router.get("/estadisticas/ventas-por-hora", response_model=VentasPorHoraOut)
def ventas_por_hora(desde: str | None = None, hasta: str | None = None, solo_pagados: bool = True,
                    db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    d, h = _rango(desde, hasta)
    return VentasPorHoraOut(desde=d.isoformat(), hasta=h.isoformat(), solo_pagados=solo_pagados,
                            horas=estadisticas_service.ventas_por_hora(db, d, h, solo_pagados))


@router.get("/estadisticas/pedidos-por-estado", response_model=PedidosPorEstadoOut)
def pedidos_por_estado(desde: str | None = None, hasta: str | None = None,
                       db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    d, h = _rango(desde, hasta)
    return PedidosPorEstadoOut(desde=d.isoformat(), hasta=h.isoformat(),
                               **estadisticas_service.pedidos_por_estado(db, d, h))
