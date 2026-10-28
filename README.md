# Backend de la pizzería (FastAPI + SQLAlchemy + MySQL)

Implementa el contrato `contratos_api_md.pdf`: prefijo `/api`, errores con `codigo` y `mensaje`,
roles estrictos y los 14 endpoints. Requisitos: Python 3.10+ y MySQL.

## Puesta en marcha (PowerShell)

```powershell
& "C:\Program Files\MySQL\MySQL Server 9.0\bin\mysql.exe" -u root -p --default-character-set=utf8mb4 -e "source sql/pizzeria.sql"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # y escribe tu contraseña de MySQL en DB_PASSWORD
uvicorn app.main:app --reload
```

Documentación interactiva: http://localhost:8000/docs
(haz login en `POST /api/auth/login`, copia el `token` y pégalo en el botón *Authorize*).

## Pruebas (no necesitan MySQL: usan SQLite en memoria con los datos de `sql/pizzeria.sql`)

```powershell
pip install -r requirements-dev.txt
pytest
```

Para probar contra tu MySQL real (recrea la base `pizzeria` en cada prueba, así que no lo uses con datos que quieras conservar):

```powershell
$env:PROBAR_CON_MYSQL = "1"
pytest
```

Cubren el recorrido del contrato: login → menú → crear pedido → cola de cocina → marcar lista →
pedidos listos → entregar → estadísticas, más todos los códigos de error.

## Usuarios de prueba (cámbialos antes del despliegue)

| Usuario   | Contraseña   | Rol           |
|-----------|--------------|---------------|
| admin     | admin123     | administrador |
| recepcion | recepcion123 | recepcionista |
| cocina    | cocina123    | cocinero      |

## Endpoints

| Rol            | Método | Ruta                                  |
|----------------|--------|---------------------------------------|
| público        | POST   | /api/auth/login                       |
| público        | GET    | /api/menu                             |
| público        | GET    | /api/productos/{id}                   |
| público        | GET    | /api/ingredientes                     |
| público        | POST   | /api/pedidos                          |
| público        | GET    | /api/pedidos/{id}/estado              |
| cocinero       | GET    | /api/cocina/cola                      |
| cocinero       | PATCH  | /api/cocina/items/{item_id}/lista     |
| recepcionista  | GET    | /api/pedidos                          |
| recepcionista  | PATCH  | /api/pedidos/{id}/entregar            |
| administrador  | PUT    | /api/admin/productos/{id}/precio      |
| administrador  | PUT    | /api/admin/ingredientes/{id}/precio   |
| administrador  | GET    | /api/admin/historial-precios          |
| administrador  | GET    | /api/admin/estadisticas               |

## Estructura

```
app/
  main.py  config.py  database.py  seguridad.py  errores.py  tiempo.py
  models/     tablas (clases del diagrama UML)
  schemas/    forma exacta de las peticiones y respuestas del contrato
  routers/    endpoints por rol
  services/   reglas de negocio y transacciones
sql/pizzeria.sql
tests/        pruebas del contrato
```

## Notas

- Todos los errores usan `{"error": {"codigo", "mensaje"}}`. JSON mal formado o datos faltantes → 400;
  reglas de negocio → 422; conflictos de estado → 409.
- El dinero sale como número en el JSON (por ejemplo `120.0`).
- Si el frontend corre en otro puerto, pon su dirección en `CORS_ORIGINS` del `.env`.
