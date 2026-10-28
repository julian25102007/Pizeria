"""Endpoints públicos del cliente: menú, detalle de producto e ingredientes."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.errores import ApiError
from app.models import Ingrediente, Producto
from app.models.enums import TipoProducto
from app.schemas.comun import IdNombre, IdNombreExtra
from app.schemas.producto import (IngredientesOut, MenuOut, ProductoDetalle,
                                  ProductoMenu)

router = APIRouter(tags=["Cliente (público)"])


def _producto_menu(p: Producto) -> dict:
    return dict(id=p.id, nombre=p.nombre, descripcion=p.descripcion, tipo=p.tipo,
                precio=p.precio, imagen_url=p.imagen_url)


@router.get("/menu", response_model=MenuOut)
def ver_menu(tipo: TipoProducto | None = None, db: Session = Depends(get_db)):
    consulta = select(Producto).where(Producto.activo.is_(True)).order_by(Producto.id)
    if tipo:
        consulta = consulta.where(Producto.tipo == tipo)
    return MenuOut(productos=[ProductoMenu(**_producto_menu(p)) for p in db.scalars(consulta)])


@router.get("/productos/{producto_id}", response_model=ProductoDetalle)
def detalle_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.scalars(
        select(Producto).where(Producto.id == producto_id)
        .options(selectinload(Producto.ingredientes))
    ).first()
    if producto is None or not producto.activo:
        raise ApiError(404, "PRODUCTO_NO_ENCONTRADO", f"No existe el producto {producto_id}")
    base = sorted(producto.ingredientes, key=lambda i: i.id)  # bebidas: lista vacía
    return ProductoDetalle(**_producto_menu(producto),
                           ingredientes_base=[IdNombre(id=i.id, nombre=i.nombre) for i in base])


@router.get("/ingredientes", response_model=IngredientesOut)
def listar_ingredientes(db: Session = Depends(get_db)):
    consulta = select(Ingrediente).where(Ingrediente.activo.is_(True)).order_by(Ingrediente.id)
    return IngredientesOut(ingredientes=[
        IdNombreExtra(id=i.id, nombre=i.nombre, precio_extra=i.precio_extra)
        for i in db.scalars(consulta)
    ])
