from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.errores import registrar_manejadores
from app.routers import admin, auth, cocina, menu, pedidos

app = FastAPI(title="API Pizzería", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
registrar_manejadores(app)


for router in (auth.router, menu.router, pedidos.router, cocina.router, admin.router):
    app.include_router(router, prefix="/api")


@app.get("/", tags=["Estado"])
def raiz():
    return {"mensaje": "API de la pizzería funcionando", "docs": "/docs"}
