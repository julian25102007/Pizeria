from sqlalchemy import true, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import Rol, columna_enum


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    usuario: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(columna_enum(Rol))
    activo: Mapped[bool] = mapped_column(default=True, server_default=true())
