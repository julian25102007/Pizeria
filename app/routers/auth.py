from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.errores import ApiError
from app.models import Usuario
from app.schemas.usuario import LoginIn, LoginOut, UsuarioLogin
from app.seguridad import crear_token, verificar_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    """Público. Mismo mensaje para usuario inexistente, contraseña mala o usuario inactivo."""
    usuario = db.scalars(select(Usuario).where(Usuario.usuario == datos.usuario)).first()
    if (usuario is None or not usuario.activo
            or not verificar_password(datos.password, usuario.password_hash)):
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos")
    return LoginOut(
        token=crear_token(usuario),
        expira_en=config.TOKEN_MINUTES * 60,
        usuario=UsuarioLogin(id=usuario.id, nombre=usuario.nombre, rol=usuario.rol),
    )
