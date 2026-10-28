"""Formato de error único del contrato:
{"error": {"codigo": "PEDIDO_NO_ENCONTRADO", "mensaje": "No existe el pedido 15"}}"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, codigo: str, mensaje: str):
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje


def _respuesta(status: int, codigo: str, mensaje: str, headers: dict | None = None):
    return JSONResponse(
        status_code=status,
        content={"error": {"codigo": codigo, "mensaje": mensaje}},
        headers=headers,
    )


_CODIGOS_HTTP = {
    404: "NO_ENCONTRADO",
    405: "METODO_NO_PERMITIDO",
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return _respuesta(exc.status, exc.codigo, exc.mensaje, headers)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        errores = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errores):
            return _respuesta(400, "JSON_INVALIDO", "El cuerpo de la petición no es un JSON válido")
        primero = errores[0]
        campo = ".".join(str(x) for x in primero.get("loc", ()) if x not in ("body", "query", "path"))
        detalle = f"{campo}: {primero.get('msg', 'dato inválido')}" if campo else primero.get("msg", "dato inválido")
        return _respuesta(400, "DATOS_INVALIDOS", f"Dato inválido o faltante ({detalle})")

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        codigo = _CODIGOS_HTTP.get(exc.status_code, "ERROR")
        return _respuesta(exc.status_code, codigo, str(exc.detail))

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception):
        return _respuesta(500, "ERROR_INTERNO", "Ocurrió un error inesperado en el servidor")
