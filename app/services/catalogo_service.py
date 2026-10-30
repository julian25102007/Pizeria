"""Alta y baja lógica de productos e ingredientes."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errores import ApiError
from app.models import Ingrediente, Producto
from app.models.enums import TipoProducto
from app.services.precio_service import _validar


def _nombre(db: Session, modelo, texto: str, maximo: int) -> str:
    nombre = (texto or "").strip()
    if not nombre or len(nombre) > maximo:
        raise ApiError(422, "NOMBRE_INVALIDO", f"El nombre debe tener entre 1 y {maximo} caracteres")
    if db.scalars(select(modelo).where(modelo.nombre == nombre)).first():
        raise ApiError(409, "NOMBRE_DUPLICADO", f"Ya existe '{nombre}' (puede estar eliminado)")
    return nombre


def crear_producto(db: Session, datos) -> Producto:
    nombre = _nombre(db, Producto, datos.nombre, 80)
    _validar(datos.precio, permite_cero=False, campo="El precio")
    ids = set(datos.ingredientes_base)
    if ids and datos.tipo == TipoProducto.bebida:
        raise ApiError(422, "BASE_INVALIDA", "Una bebida no lleva ingredientes base")
    ingredientes = []
    if ids:
        ingredientes = list(db.scalars(
            select(Ingrediente).where(Ingrediente.id.in_(ids), Ingrediente.activo.is_(True))))
        if len(ingredientes) != len(ids):
            raise ApiError(422, "INGREDIENTE_NO_ENCONTRADO",
                           "Algún ingrediente base no existe o está eliminado")
    producto = Producto(nombre=nombre, descripcion=datos.descripcion, tipo=datos.tipo,
                        precio=datos.precio, imagen_url=datos.imagen_url,
                        ingredientes=ingredientes)
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def crear_ingrediente(db: Session, datos) -> Ingrediente:
    nombre = _nombre(db, Ingrediente, datos.nombre, 60)
    _validar(datos.precio_extra, permite_cero=True, campo="El precio extra")
    ingrediente = Ingrediente(nombre=nombre, precio_extra=datos.precio_extra)
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


def eliminar_producto(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None or not producto.activo:
        raise ApiError(404, "PRODUCTO_NO_ENCONTRADO", f"No existe el producto {producto_id}")
    producto.activo = False
    db.commit()
    return producto


def eliminar_ingrediente(db: Session, ingrediente_id: int) -> Ingrediente:
    ingrediente = db.get(Ingrediente, ingrediente_id)
    if ingrediente is None or not ingrediente.activo:
        raise ApiError(404, "INGREDIENTE_NO_ENCONTRADO", f"No existe el ingrediente {ingrediente_id}")
    ingrediente.activo = False
    db.commit()
    return ingrediente