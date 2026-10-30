from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.models.enums import Accion, Rol
from app.schemas.comun import IdNombre
from app.schemas.pedido import ColaOut, ItemCola, ItemListaOut
from app.seguridad import requiere_rol
from app.services import pedido_service

router = APIRouter(prefix="/cocina", tags=["Cocinero"])
solo_cocinero = requiere_rol(Rol.cocinero)


@router.get("/cola", response_model=ColaOut)
def cola(db: Session = Depends(get_db), _: Usuario = Depends(solo_cocinero)):
    cola = []
    for d in pedido_service.cola_cocina(db):
        quitados = [p.ingrediente for p in d.personalizaciones if p.accion == Accion.quitado]
        agregados = [p.ingrediente for p in d.personalizaciones if p.accion == Accion.agregado]
        ids_quitados = {i.id for i in quitados}

        finales = [i for i in sorted(d.producto.ingredientes, key=lambda i: i.id)
                   if i.id not in ids_quitados] + sorted(agregados, key=lambda i: i.id)
        cola.append(ItemCola(
            item_id=d.id, pedido_id=d.pedido_id, nombre_cliente=d.pedido.nombre_cliente,
            pizza=d.producto.nombre, fecha_creacion=d.pedido.fecha_creacion,
            ingredientes=[IdNombre(id=i.id, nombre=i.nombre) for i in finales],
            quitados=[IdNombre(id=i.id, nombre=i.nombre) for i in quitados],
            agregados=[IdNombre(id=i.id, nombre=i.nombre) for i in agregados],
        ))
    return ColaOut(cola=cola)


@router.patch("/items/{item_id}/lista", response_model=ItemListaOut)
def marcar_lista(item_id: int, db: Session = Depends(get_db), _: Usuario = Depends(solo_cocinero)):
    detalle = pedido_service.marcar_pizza_lista(db, item_id)
    return ItemListaOut(item_id=detalle.id, estado_cocina=detalle.estado_cocina,
                        pedido_id=detalle.pedido_id, pedido_estado=detalle.pedido.estado)
