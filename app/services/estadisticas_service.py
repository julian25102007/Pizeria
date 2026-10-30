"""Ventas del día y producto más vendido."""
from datetime import date, timedelta

from sqlalchemy import desc, extract, func, select
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


# ---------------------------------------------------------------- datos para gráficas
def _campo_y_filtros(desde: date, hasta: date, solo_pagados: bool):
    """Ventas = pedidos cobrados (por fecha de pago). Si solo_pagados=False, por fecha de creación."""
    campo = Pedido.fecha_pago if solo_pagados else Pedido.fecha_creacion
    filtros = [campo >= rango_dia(desde)[0], campo < rango_dia(hasta)[1]]
    if solo_pagados:
        filtros.append(Pedido.pagado.is_(True))
    return campo, filtros


def ventas_por_dia(db: Session, desde: date, hasta: date, solo_pagados: bool) -> list[dict]:
    campo, filtros = _campo_y_filtros(desde, hasta, solo_pagados)
    dia = func.date(campo)
    filas = db.execute(
        select(dia, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0))
        .where(*filtros).group_by(dia)
    ).all()
    por_dia = {str(f): (n, t) for f, n, t in filas}
    dias, d = [], desde
    while d <= hasta:  # rellena con 0 los días sin ventas para que la gráfica no tenga huecos
        n, t = por_dia.get(d.isoformat(), (0, 0))
        dias.append({"fecha": d.isoformat(), "num_pedidos": n, "total": t})
        d += timedelta(days=1)
    return dias


def productos_vendidos(db: Session, desde: date, hasta: date, solo_pagados: bool,
                       limite: int) -> list[dict]:
    _, filtros = _campo_y_filtros(desde, hasta, solo_pagados)
    filas = db.execute(
        select(Producto.id, Producto.nombre,
               func.sum(DetallePedido.cantidad).label("unidades"),
               func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario).label("ingresos"))
        .select_from(DetallePedido)
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .join(Producto, Producto.id == DetallePedido.producto_id)
        .where(*filtros)
        .group_by(Producto.id, Producto.nombre)
        .order_by(desc("unidades"), Producto.id)
        .limit(limite)
    ).all()
    return [{"id": f.id, "nombre": f.nombre, "unidades": int(f.unidades), "ingresos": f.ingresos}
            for f in filas]


def ventas_por_hora(db: Session, desde: date, hasta: date, solo_pagados: bool) -> list[dict]:
    campo, filtros = _campo_y_filtros(desde, hasta, solo_pagados)
    hora = extract("hour", campo)
    filas = db.execute(
        select(hora, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0))
        .where(*filtros).group_by(hora)
    ).all()
    por_hora = {int(h): (n, t) for h, n, t in filas}
    return [{"hora": h, "num_pedidos": por_hora.get(h, (0, 0))[0], "total": por_hora.get(h, (0, 0))[1]}
            for h in range(24)]


def pedidos_por_estado(db: Session, desde: date, hasta: date) -> dict:
    filas = db.execute(
        select(Pedido.estado, func.count(Pedido.id))
        .where(Pedido.fecha_creacion >= rango_dia(desde)[0], Pedido.fecha_creacion < rango_dia(hasta)[1])
        .group_by(Pedido.estado)
    ).all()
    conteo = {str(getattr(e, "value", e)): n for e, n in filas}
    return {k: conteo.get(k, 0) for k in ("pendiente", "listo", "entregado")}
