"""Ventas del día y producto más vendido."""
from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import DetallePedido, Pedido, Producto
from app.tiempo import rango_dia


def estadisticas_del_dia(db: Session, dia: date) -> dict:
    inicio, fin = rango_dia(dia)
    cuando = (Pedido.fecha_creacion >= inicio, Pedido.fecha_creacion < fin)

    num_pedidos, total_ventas = db.execute(
        select(func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0)).where(*cuando)
    ).one()

    fila = db.execute(
        select(Producto.id, Producto.nombre, func.sum(DetallePedido.cantidad).label("unidades"))
        .select_from(DetallePedido)
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .join(Producto, Producto.id == DetallePedido.producto_id)
        .where(*cuando)
        .group_by(Producto.id, Producto.nombre)
        .order_by(desc("unidades"), Producto.id)
        .limit(1)
    ).first()

    return {
        "fecha": dia.isoformat(),
        "ventas_dia": {"num_pedidos": num_pedidos, "total_ventas": total_ventas},
        "producto_mas_vendido": (
            {"id": fila.id, "nombre": fila.nombre, "unidades": int(fila.unidades)} if fila else None
        ),
    }
