"""Fechas: formato ISO 8601 sin fracciones de segundo, como en el contrato."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.errores import ApiError

ZONA = ZoneInfo("America/Mexico_City")


def ahora() -> datetime:
    return datetime.now(ZONA).replace(tzinfo=None, microsecond=0)


def hoy() -> date:
    return datetime.now(ZONA).date()


def parsear_fecha(texto: str | None) -> date:
    """Convierte 'YYYY-MM-DD' en fecha; si falta usa hoy. Error 400 FECHA_INVALIDA."""
    if texto is None:
        return hoy()
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(400, "FECHA_INVALIDA", "La fecha debe tener el formato YYYY-MM-DD")


def rango_dia(dia: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(dia, time.min)
    return inicio, inicio + timedelta(days=1)