"""Pruebas contra SQLite en memoria, cargando los INSERT de sql/pizzeria.sql.
No necesitas MySQL para correrlas."""
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models  # noqa: F401  (registra las tablas)

SQL = Path(__file__).resolve().parent.parent / "sql" / "pizzeria.sql"


def _recargar_mysql():
    """Borra y recrea la base `pizzeria` con sql/pizzeria.sql (MySQL real)."""
    import pymysql
    from pymysql.constants import CLIENT

    from app import config
    from app.database import engine

    con = pymysql.connect(host=config.DB_HOST, port=int(config.DB_PORT), user=config.DB_USER,
                          password=config.DB_PASSWORD, charset="utf8mb4", autocommit=True,
                          client_flag=CLIENT.MULTI_STATEMENTS)
    with con.cursor() as cur:
        cur.execute(SQL.read_text(encoding="utf-8"))
        while cur.nextset():
            pass
    con.close()
    engine.dispose()  # las conexiones viejas apuntaban a la base borrada


@pytest.fixture()
def client():
    # PROBAR_CON_MYSQL=1 -> usa tu MySQL real (según el .env); si no, SQLite en memoria
    if os.getenv("PROBAR_CON_MYSQL"):
        _recargar_mysql()
        yield TestClient(app)
        return

    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(motor)
    with motor.begin() as con:
        for sentencia in re.findall(r"INSERT INTO .*?;", SQL.read_text(encoding="utf-8"), re.S):
            con.execute(text(sentencia))

    Sesion = sessionmaker(bind=motor, autoflush=False)

    def _db():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    yield TestClient(app)
    app.dependency_overrides.clear()


CLAVES = {"admin": "admin123", "recepcion": "recepcion123", "cocina": "cocina123"}


@pytest.fixture()
def tokens(client):
    def _login(usuario):
        r = client.post("/api/auth/login", json={"usuario": usuario, "password": CLAVES[usuario]})
        assert r.status_code == 200, r.text
        return {"Authorization": "Bearer " + r.json()["token"]}

    return {u: _login(u) for u in CLAVES}
