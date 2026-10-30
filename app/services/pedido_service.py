"""Reglas de negocio de los pedidos (ver contrato de API)."""
from datetime import date
from decimal import Decimal
from sqlalchemy import exists, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.errores import ApiError
from app.models import (DetallePedido, Ingrediente, Pedido, Personalizacion,
                        Producto, Usuario)
from app.models.enums import Accion, EstadoCocina, EstadoPedido, TipoProducto
from app.schemas.pedido import PedidoIn
from app.tiempo import ahora, rango_dia


def consulta_pedidos():
    """SELECT de pedidos con todo lo necesario ya cargado."""
    return select(Pedido).options(
        selectinload(Pedido.detalles).selectinload(DetallePedido.producto),
        selectinload(Pedido.detalles)
        .selectinload(DetallePedido.personalizaciones)
        .selectinload(Personalizacion.ingrediente),
    )


def obtener_pedido(db: Session, pedido_id: int) -> Pedido:
    pedido = db.scalars(consulta_pedidos().where(Pedido.id == pedido_id)).first()
    if pedido is None:
        raise ApiError(404, "PEDIDO_NO_ENCONTRADO", f"No existe el pedido {pedido_id}")
    return pedido


# ---------------------------------------------------------------- crear
def crear_pedido(db: Session, datos: PedidoIn) -> Pedido:
    """Crea pedido + items + cambios de ingredientes en UNA transacción.
    El cliente nunca envía precios: se calculan con los precios actuales."""
    nombre = (datos.nombre_cliente or "").strip()
    if not nombre or len(nombre) > 80:
        raise ApiError(422, "NOMBRE_INVALIDO",
                       "El nombre del cliente es obligatorio y debe tener máximo 80 caracteres")
    if not datos.items:
        raise ApiError(422, "PEDIDO_VACIO", "El pedido debe tener al menos un producto")

    pedido = Pedido(nombre_cliente=nombre, total=Decimal("0"), fecha_creacion=ahora())
    total = Decimal("0")
    hay_pizzas = False

    for item in datos.items:
        producto = db.get(Producto, item.producto_id)
        if producto is None or not producto.activo:
            raise ApiError(422, "PRODUCTO_NO_DISPONIBLE",
                           f"El producto {item.producto_id} no existe o no está disponible")

        es_pizza = producto.tipo == TipoProducto.pizza
        cantidad_valida = item.cantidad == 1 if es_pizza else 1 <= item.cantidad <= 10
        if not cantidad_valida:
            raise ApiError(422, "CANTIDAD_INVALIDA",
                           "Las pizzas van de una en una (cantidad 1) y las bebidas de 1 a 10")

        quitar, agregar = item.ingredientes_quitar, item.ingredientes_agregar
        if not es_pizza and (quitar or agregar):
            raise ApiError(422, "BEBIDA_NO_PERSONALIZABLE",
                           f"{producto.nombre} no admite cambios de ingredientes")

        detalle = DetallePedido(producto=producto, cantidad=item.cantidad)
        extras = Decimal("0")

        if es_pizza:
            hay_pizzas = True
            todos = quitar + agregar
            if len(set(todos)) != len(todos):
                raise ApiError(422, "INGREDIENTES_DUPLICADOS",
                               "Un ingrediente no puede repetirse ni estar en quitar y agregar a la vez")

            base = {i.id: i for i in producto.ingredientes}
            for ing_id in quitar:
                if ing_id not in base:
                    raise ApiError(422, "INGREDIENTE_NO_QUITABLE",
                                   f"El ingrediente {ing_id} no está en la receta base de {producto.nombre}")
                detalle.personalizaciones.append(
                    Personalizacion(ingrediente=base[ing_id], accion=Accion.quitado,
                                    precio_extra=Decimal("0"))
                )
            for ing_id in agregar:
                ing = db.get(Ingrediente, ing_id)
                if ing is None or not ing.activo or ing_id in base:
                    raise ApiError(422, "INGREDIENTE_NO_AGREGABLE",
                                   f"El ingrediente {ing_id} no se puede agregar a {producto.nombre}")
                extras += ing.precio_extra
                detalle.personalizaciones.append(
                    Personalizacion(ingrediente=ing, accion=Accion.agregado,
                                    precio_extra=ing.precio_extra)
                )
        else:
            detalle.estado_cocina = EstadoCocina.lista  # las bebidas no pasan por cocina

        # precio_unitario = precio del producto + extras de lo agregado
        detalle.precio_unitario = producto.precio + extras
        total += detalle.precio_unitario * item.cantidad
        pedido.detalles.append(detalle)

    pedido.total = total
    if hay_pizzas:
        pedido.estado = EstadoPedido.pendiente
    else:  # solo bebidas: nace listo
        pedido.estado = EstadoPedido.listo
        pedido.fecha_listo = pedido.fecha_creacion

    db.add(pedido)
    db.commit()
    return obtener_pedido(db, pedido.id)


# ---------------------------------------------------------------- cocina
def cola_cocina(db: Session) -> list[DetallePedido]:
    """Pizzas pendientes, la más antigua primero."""
    consulta = (
        select(DetallePedido)
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .join(Producto, Producto.id == DetallePedido.producto_id)
        .where(Producto.tipo == TipoProducto.pizza,
               DetallePedido.estado_cocina == EstadoCocina.pendiente)
        .options(
            selectinload(DetallePedido.pedido),
            selectinload(DetallePedido.producto).selectinload(Producto.ingredientes),
            selectinload(DetallePedido.personalizaciones).selectinload(Personalizacion.ingrediente),
        )
        .order_by(Pedido.fecha_creacion, DetallePedido.id)
    )
    return list(db.scalars(consulta).all())


def marcar_pizza_lista(db: Session, item_id: int) -> DetallePedido:
    detalle = db.get(DetallePedido, item_id)
    if detalle is None:
        raise ApiError(404, "ITEM_NO_ENCONTRADO", f"No existe el item {item_id}")
    if detalle.producto.tipo != TipoProducto.pizza:
        raise ApiError(422, "ITEM_NO_ES_PIZZA", f"El item {item_id} no es una pizza")
    if detalle.estado_cocina == EstadoCocina.lista:
        raise ApiError(409, "ITEM_YA_LISTO", f"El item {item_id} ya estaba marcado como listo")

    pedido_id = detalle.pedido_id
    detalle.estado_cocina = EstadoCocina.lista
    db.flush()

    # Cierra el pedido solo si ya no quedan pizzas pendientes (consulta del contrato)
    db.execute(
        update(Pedido)
        .where(
            Pedido.id == pedido_id,
            Pedido.estado == EstadoPedido.pendiente,
            ~exists().where(DetallePedido.pedido_id == pedido_id,
                            DetallePedido.estado_cocina == EstadoCocina.pendiente),
        )
        .values(estado=EstadoPedido.listo, fecha_listo=ahora())
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return db.get(DetallePedido, item_id)


# ---------------------------------------------------------------- recepción
def listar_pedidos(db: Session, estados: list[EstadoPedido], dia: date) -> list[Pedido]:
    inicio, fin = rango_dia(dia)
    consulta = (
        consulta_pedidos()
        .where(Pedido.estado.in_(estados),
               Pedido.fecha_creacion >= inicio, Pedido.fecha_creacion < fin)
        .order_by(Pedido.fecha_listo, Pedido.id)
    )
    return list(db.scalars(consulta).all())


def entregar_pedido(db: Session, pedido_id: int, usuario: Usuario) -> Pedido:
    if db.get(Pedido, pedido_id) is None:
        raise ApiError(404, "PEDIDO_NO_ENCONTRADO", f"No existe el pedido {pedido_id}")

    resultado = db.execute(
        update(Pedido)
        .where(Pedido.id == pedido_id, Pedido.estado == EstadoPedido.listo)
        .values(estado=EstadoPedido.entregado, fecha_entrega=ahora(), entregado_por=usuario.id)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount == 0:
        db.rollback()
        raise ApiError(409, "PEDIDO_NO_LISTO",
                    f"El pedido {pedido_id} no está en estado 'listo' (solo se entrega lo que está listo)")
    db.commit()
    return db.get(Pedido, pedido_id)


def historial_pedidos(db: Session, estados, desde, hasta, limite: int, offset: int):
    filtros = []
    if estados:
        filtros.append(Pedido.estado.in_(estados))
    if desde:
        filtros.append(Pedido.fecha_creacion >= rango_dia(desde)[0])
    if hasta:
        filtros.append(Pedido.fecha_creacion < rango_dia(hasta)[1])
    total = db.scalar(select(func.count()).select_from(Pedido).where(*filtros))
    pedidos = list(db.scalars(
        consulta_pedidos().where(*filtros)
        .order_by(Pedido.fecha_creacion.desc(), Pedido.id.desc())
        .limit(limite).offset(offset)
    ).all())
    return total, pedidos
