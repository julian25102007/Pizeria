"""Fechas: formato ISO 8601 sin fracciones de segundo, como en el contrato."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.errores import ApiError

ZONA = ZoneInfo("America/Mexico_City")


def ahora() -> datetime:
    return datetime.now(ZONA).replace(tzinfo=None, microsecond=0)


def hoy() -> date:
    return datetime.now(ZONA).date()