from sqlalchemy import func, select
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HistorialPrecio, Ingrediente, Producto, Usuario
from app.models.enums import Rol, TipoReferencia
from app.schemas.admin import (CambioHistorial, CambioPrecioOut, EstadisticasOut,
                               HistorialOut, PrecioIngredienteIn, PrecioProductoIn)
from app.seguridad import requiere_rol
from app.services import estadisticas_service, precio_service
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
