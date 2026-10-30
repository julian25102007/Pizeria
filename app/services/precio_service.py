"""Cambios de precio con historial (misma transacción)."""
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.errores import ApiError
from app.models import HistorialPrecio, Ingrediente, Producto, Usuario
from app.models.enums import TipoReferencia

MAXIMO = Decimal("999999.99")


def _validar(valor: Decimal, permite_cero: bool, campo: str) -> None:
    try:
        valido = (
            valor.is_finite()
            and valor == valor.quantize(Decimal("0.01"))
            and valor <= MAXIMO
            and (valor >= 0 if permite_cero else valor > 0)
        )
    except InvalidOperation:
        valido = False
    if not valido:
        regla = "0 o mayor" if permite_cero else "mayor que 0"
        raise ApiError(422, "PRECIO_INVALIDO",
                       f"{campo} debe ser {regla}, con máximo 2 decimales")


def _guardar(db: Session, tipo: TipoReferencia, entidad, campo: str, nuevo: Decimal, usuario: Usuario):
    anterior = getattr(entidad, campo)
    db.add(HistorialPrecio(tipo=tipo, referencia_id=entidad.id, precio_anterior=anterior,
                           precio_nuevo=nuevo, usuario_id=usuario.id))
    setattr(entidad, campo, nuevo)
    db.commit()
    return {"id": entidad.id, "nombre": entidad.nombre,
            "precio_anterior": anterior, "precio_nuevo": nuevo}


def cambiar_precio_producto(db: Session, producto_id: int, nuevo: Decimal, usuario: Usuario):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise ApiError(404, "PRODUCTO_NO_ENCONTRADO", f"No existe el producto {producto_id}")
    _validar(nuevo, permite_cero=False, campo="El precio")
    return _guardar(db, TipoReferencia.producto, producto, "precio", nuevo, usuario)


def cambiar_precio_ingrediente(db: Session, ingrediente_id: int, nuevo: Decimal, usuario: Usuario):
    ingrediente = db.get(Ingrediente, ingrediente_id)
    if ingrediente is None:
        raise ApiError(404, "INGREDIENTE_NO_ENCONTRADO", f"No existe el ingrediente {ingrediente_id}")
    _validar(nuevo, permite_cero=True, campo="El precio extra")
    return _guardar(db, TipoReferencia.ingrediente, ingrediente, "precio_extra", nuevo, usuario)
