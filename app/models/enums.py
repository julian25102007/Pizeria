"""Enumeraciones (los ENUM de MySQL)."""
import enum

from sqlalchemy import Enum as SAEnum


class Rol(str, enum.Enum):
    administrador = "administrador"
    recepcionista = "recepcionista"
    cocinero = "cocinero"


class TipoProducto(str, enum.Enum):
    pizza = "pizza"
    bebida = "bebida"


class EstadoPedido(str, enum.Enum):
    pendiente = "pendiente"
    listo = "listo"
    entregado = "entregado"


class EstadoCocina(str, enum.Enum):
    pendiente = "pendiente"
    lista = "lista"


class Accion(str, enum.Enum):
    quitado = "quitado"
    agregado = "agregado"


class TipoReferencia(str, enum.Enum):
    producto = "producto"
    ingrediente = "ingrediente"


def columna_enum(clase):
    """Guarda en la BD el valor en minúsculas, igual que el script SQL."""
    return SAEnum(
        clase,
        values_callable=lambda e: [m.value for m in e],
        name=clase.__name__.lower(),
    )
