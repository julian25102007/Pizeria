from pydantic import BaseModel

from app.models.enums import TipoProducto
from app.schemas.comun import Dinero, IdNombre, IdNombreExtra


class ProductoMenu(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    tipo: TipoProducto
    precio: Dinero
    imagen_url: str | None


class MenuOut(BaseModel):
    productos: list[ProductoMenu]


class ProductoDetalle(ProductoMenu):
    ingredientes_base: list[IdNombre]


class IngredientesOut(BaseModel):
    ingredientes: list[IdNombreExtra]
