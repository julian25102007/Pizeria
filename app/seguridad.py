"""Contraseñas (bcrypt), tokens JWT y control de roles."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.errores import ApiError
from app.models import Usuario
from app.models.enums import Rol

# Authorization: Bearer <token>
esquema_bearer = HTTPBearer(auto_error=False)


def verificar_password(plano: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(plano.encode(), hash_guardado.encode())
    except ValueError:
        return False


def crear_token(usuario: Usuario) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_MINUTES)
    datos = {"sub": str(usuario.id), "rol": usuario.rol.value, "exp": expira}
    return jwt.encode(datos, config.SECRET_KEY, algorithm=config.ALGORITHM)


def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise ApiError(401, "NO_AUTENTICADO", "Falta el token de autenticación")
    try:
        datos = jwt.decode(credenciales.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        usuario = db.get(Usuario, int(datos["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise ApiError(401, "TOKEN_INVALIDO", "Token inválido o vencido")
    if usuario is None or not usuario.activo:
        raise ApiError(401, "TOKEN_INVALIDO", "Token inválido o vencido")
    return usuario


def requiere_rol(rol: Rol):
    """Uso: Depends(requiere_rol(Rol.cocinero)). Solo ese rol puede entrar."""

    def dependencia(usuario: Usuario = Depends(get_usuario_actual)) -> Usuario:
        if usuario.rol != rol:
            raise ApiError(403, "PERMISO_DENEGADO", f"Este endpoint es solo para el rol {rol.value}")
        return usuario

    return dependencia
