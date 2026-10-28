from pydantic import BaseModel, Field

from app.models.enums import Rol


class LoginIn(BaseModel):
    usuario: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UsuarioLogin(BaseModel):
    id: int
    nombre: str
    rol: Rol


class LoginOut(BaseModel):
    token: str
    expira_en: int  # segundos
    usuario: UsuarioLogin
