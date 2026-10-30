"""Pruebas del contrato de API (contratos_api_md.pdf)."""
import pytest

PEDIDO_ANA = {
    "nombre_cliente": "Ana",
    "items": [
        {"producto_id": 4, "cantidad": 1, "ingredientes_quitar": [8], "ingredientes_agregar": [16]},
        {"producto_id": 7, "cantidad": 2},
    ],
}


def codigo(r):
    return r.json()["error"]["codigo"]



def test_login(client):
    r = client.post("/api/auth/login", json={"usuario": "admin", "password": "admin123"})
    assert r.status_code == 200
    d = r.json()
    assert d["expira_en"] == 28800
    assert d["usuario"] == {"id": 1, "nombre": "Administrador", "rol": "administrador"}
    assert d["token"]


def test_login_errores(client):
    r = client.post("/api/auth/login", json={"usuario": "admin", "password": "mala"})
    assert r.status_code == 401 and codigo(r) == "CREDENCIALES_INVALIDAS"
    r2 = client.post("/api/auth/login", json={"usuario": "nadie", "password": "x"})
    assert r.json() == r2.json()
    assert client.post("/api/auth/login", json={"usuario": "admin"}).status_code == 400
    r = client.post("/api/auth/login", content="{esto no es json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and codigo(r) == "JSON_INVALIDO"


def test_permisos(client, tokens):
    r = client.get("/api/cocina/cola")
    assert r.status_code == 401 and codigo(r) == "NO_AUTENTICADO"
    r = client.get("/api/cocina/cola", headers={"Authorization": "Bearer falso"})
    assert r.status_code == 401 and codigo(r) == "TOKEN_INVALIDO"
    assert client.get("/api/pedidos", headers=tokens["cocina"]).status_code == 403
    assert client.get("/api/cocina/cola", headers=tokens["admin"]).status_code == 403
    assert client.get("/api/admin/estadisticas", headers=tokens["recepcion"]).status_code == 403


def test_error_en_rutas_inexistentes(client):
    r = client.get("/api/no-existe")
    assert r.status_code == 404 and set(r.json()["error"]) == {"codigo", "mensaje"}



def test_menu_producto_ingredientes(client):
    productos = client.get("/api/menu").json()["productos"]
    assert len(productos) == 8
    assert productos[0] == {"id": 1, "nombre": "Margarita",
                            "descripcion": "Clásica con mozzarella y albahaca fresca",
                            "tipo": "pizza", "precio": 120.0, "imagen_url": None}
    assert len(client.get("/api/menu?tipo=bebida").json()["productos"]) == 2
    assert client.get("/api/menu?tipo=otra").status_code == 400

    mex = client.get("/api/productos/4").json()
    assert [i["id"] for i in mex["ingredientes_base"]] == [1, 2, 6, 7, 8]
    assert client.get("/api/productos/7").json()["ingredientes_base"] == []
    r = client.get("/api/productos/999")
    assert r.status_code == 404 and codigo(r) == "PRODUCTO_NO_ENCONTRADO"

    ings = client.get("/api/ingredientes").json()["ingredientes"]
    assert len(ings) == 16 and {"id": 16, "nombre": "Tocino", "precio_extra": 20.0} in ings



def test_flujo_completo(client, tokens):

    r = client.post("/api/pedidos", json=PEDIDO_ANA)
    assert r.status_code == 201
    p = r.json()
    assert p["estado"] == "pendiente" and p["total"] == 215.0
    assert "." not in p["fecha_creacion"]
    mex, ref = p["items"]
    assert mex["precio_unitario"] == 165.0 and mex["ingredientes_quitados"] == [{"id": 8, "nombre": "Cebolla"}]
    assert mex["ingredientes_agregados"] == [{"id": 16, "nombre": "Tocino", "precio_extra": 20.0}]
    assert ref["cantidad"] == 2 and ref["precio_unitario"] == 25.0 and ref["ingredientes_quitados"] == []


    est = client.get(f"/api/pedidos/{p['id']}/estado").json()
    assert [i["estado_cocina"] for i in est["items"]] == ["pendiente", "lista"]
    r = client.get("/api/pedidos/999/estado")
    assert r.status_code == 404 and codigo(r) == "PEDIDO_NO_ENCONTRADO"


    cola = client.get("/api/cocina/cola", headers=tokens["cocina"]).json()["cola"]
    assert len(cola) == 1
    item = cola[0]
    assert item["pizza"] == "Mexicana" and item["quitados"] == [{"id": 8, "nombre": "Cebolla"}]
    assert [i["id"] for i in item["ingredientes"]] == [1, 2, 6, 7, 16]


    assert client.get("/api/pedidos", headers=tokens["recepcion"]).json() == {"pedidos": []}
    r = client.patch(f"/api/pedidos/{p['id']}/entregar", headers=tokens["recepcion"])
    assert r.status_code == 409 and codigo(r) == "PEDIDO_NO_LISTO"

    r = client.patch(f"/api/cocina/items/{item['item_id']}/lista", headers=tokens["cocina"])
    assert r.json() == {"item_id": item["item_id"], "estado_cocina": "lista",
                        "pedido_id": p["id"], "pedido_estado": "listo"}

    listos = client.get("/api/pedidos", headers=tokens["recepcion"]).json()["pedidos"]
    assert len(listos) == 1 and listos[0]["estado"] == "listo" and listos[0]["fecha_listo"]
    assert listos[0]["items"] == [{"nombre": "Mexicana", "cantidad": 1}, {"nombre": "Refresco", "cantidad": 2}]

    r = client.patch(f"/api/pedidos/{p['id']}/entregar", headers=tokens["recepcion"])
    assert r.status_code == 200 and r.json()["estado"] == "entregado" and r.json()["fecha_entrega"]
    assert codigo(client.patch(f"/api/pedidos/{p['id']}/entregar", headers=tokens["recepcion"])) == "PEDIDO_NO_LISTO"


    e = client.get("/api/admin/estadisticas", headers=tokens["admin"]).json()
    assert e["ventas_dia"] == {"num_pedidos": 1, "total_ventas": 215.0}
    assert e["producto_mas_vendido"] == {"id": 7, "nombre": "Refresco", "unidades": 2}


def test_pedido_con_dos_pizzas_cierra_al_ultima(client, tokens):
    r = client.post("/api/pedidos", json={"nombre_cliente": "Luis", "items": [
        {"producto_id": 1}, {"producto_id": 2, "ingredientes_quitar": [3]}]})
    ids = [i["item_id"] for i in r.json()["items"]]
    r1 = client.patch(f"/api/cocina/items/{ids[0]}/lista", headers=tokens["cocina"])
    assert r1.json()["pedido_estado"] == "pendiente"
    r2 = client.patch(f"/api/cocina/items/{ids[1]}/lista", headers=tokens["cocina"])
    assert r2.json()["pedido_estado"] == "listo"


def test_pedido_solo_bebidas_nace_listo(client, tokens):
    p = client.post("/api/pedidos", json={"nombre_cliente": "Eva", "items": [{"producto_id": 8, "cantidad": 3}]}).json()
    assert p["estado"] == "listo" and p["total"] == 60.0
    assert len(client.get("/api/pedidos", headers=tokens["recepcion"]).json()["pedidos"]) == 1



@pytest.mark.parametrize("cuerpo,esperado", [
    ({"items": [{"producto_id": 1}]}, "NOMBRE_INVALIDO"),
    ({"nombre_cliente": "  ", "items": [{"producto_id": 1}]}, "NOMBRE_INVALIDO"),
    ({"nombre_cliente": "x" * 81, "items": [{"producto_id": 1}]}, "NOMBRE_INVALIDO"),
    ({"nombre_cliente": "A", "items": []}, "PEDIDO_VACIO"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 999}]}, "PRODUCTO_NO_DISPONIBLE"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 1, "cantidad": 2}]}, "CANTIDAD_INVALIDA"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 7, "cantidad": 11}]}, "CANTIDAD_INVALIDA"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 7, "cantidad": 0}]}, "CANTIDAD_INVALIDA"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 7, "ingredientes_agregar": [3]}]}, "BEBIDA_NO_PERSONALIZABLE"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 1, "ingredientes_quitar": [3]}]}, "INGREDIENTE_NO_QUITABLE"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 1, "ingredientes_agregar": [2]}]}, "INGREDIENTE_NO_AGREGABLE"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 1, "ingredientes_agregar": [999]}]}, "INGREDIENTE_NO_AGREGABLE"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 1, "ingredientes_quitar": [2], "ingredientes_agregar": [2]}]}, "INGREDIENTES_DUPLICADOS"),
    ({"nombre_cliente": "A", "items": [{"producto_id": 1, "ingredientes_agregar": [3, 3]}]}, "INGREDIENTES_DUPLICADOS"),
])
def test_validaciones_pedido(client, cuerpo, esperado):
    r = client.post("/api/pedidos", json=cuerpo)
    assert r.status_code == 422 and codigo(r) == esperado


def test_pedido_con_error_no_guarda_nada(client, tokens):
    client.post("/api/pedidos", json={"nombre_cliente": "A", "items": [
        {"producto_id": 1}, {"producto_id": 7, "cantidad": 99}]})
    e = client.get("/api/admin/estadisticas", headers=tokens["admin"]).json()
    assert e["ventas_dia"]["num_pedidos"] == 0 and e["producto_mas_vendido"] is None



def test_cocina_errores(client, tokens):
    p = client.post("/api/pedidos", json=PEDIDO_ANA).json()
    pizza, bebida = p["items"][0]["item_id"], p["items"][1]["item_id"]
    c = tokens["cocina"]
    r = client.patch("/api/cocina/items/999/lista", headers=c)
    assert r.status_code == 404 and codigo(r) == "ITEM_NO_ENCONTRADO"
    r = client.patch(f"/api/cocina/items/{bebida}/lista", headers=c)
    assert r.status_code == 422 and codigo(r) == "ITEM_NO_ES_PIZZA"
    assert client.patch(f"/api/cocina/items/{pizza}/lista", headers=c).status_code == 200
    r = client.patch(f"/api/cocina/items/{pizza}/lista", headers=c)
    assert r.status_code == 409 and codigo(r) == "ITEM_YA_LISTO"
    assert client.get("/api/cocina/cola", headers=c).json() == {"cola": []}



def test_filtros_pedidos(client, tokens):
    h = tokens["recepcion"]
    r = client.get("/api/pedidos?estado=pendiente", headers=h)
    assert r.status_code == 400 and codigo(r) == "ESTADO_INVALIDO"
    r = client.get("/api/pedidos?fecha=21-10-2026", headers=h)
    assert r.status_code == 400 and codigo(r) == "FECHA_INVALIDA"
    client.post("/api/pedidos", json={"nombre_cliente": "Eva", "items": [{"producto_id": 8}]})
    assert len(client.get("/api/pedidos?estado=listo,entregado", headers=h).json()["pedidos"]) == 1
    assert client.get("/api/pedidos?estado=entregado", headers=h).json()["pedidos"] == []
    assert client.get("/api/pedidos?fecha=2020-01-01", headers=h).json()["pedidos"] == []



def test_precios_e_historial(client, tokens):
    a = tokens["admin"]
    viejo = client.post("/api/pedidos", json=PEDIDO_ANA).json()

    r = client.put("/api/admin/productos/4/precio", json={"precio": 150.00}, headers=a)
    assert r.json() == {"id": 4, "nombre": "Mexicana", "precio_anterior": 145.0, "precio_nuevo": 150.0}
    r = client.put("/api/admin/ingredientes/16/precio", json={"precio_extra": 25.00}, headers=a)
    assert r.json() == {"id": 16, "nombre": "Tocino", "precio_anterior": 20.0, "precio_nuevo": 25.0}


    assert client.get(f"/api/pedidos/{viejo['id']}/estado").json()["total"] == 215.0

    assert client.post("/api/pedidos", json=PEDIDO_ANA).json()["total"] == 225.0

    for ruta, cuerpo in [("productos/4", {"precio": 0}), ("productos/4", {"precio": -5}),
                         ("productos/4", {"precio": 10.123}), ("ingredientes/16", {"precio_extra": -1})]:
        r = client.put(f"/api/admin/{ruta}/precio", json=cuerpo, headers=a)
        assert r.status_code == 422 and codigo(r) == "PRECIO_INVALIDO", (ruta, cuerpo)
    assert client.put("/api/admin/ingredientes/16/precio", json={"precio_extra": 0}, headers=a).status_code == 200
    assert codigo(client.put("/api/admin/productos/999/precio", json={"precio": 5}, headers=a)) == "PRODUCTO_NO_ENCONTRADO"
    assert codigo(client.put("/api/admin/ingredientes/999/precio", json={"precio_extra": 5}, headers=a)) == "INGREDIENTE_NO_ENCONTRADO"
    assert client.put("/api/admin/productos/4/precio", json={}, headers=a).status_code == 400

    cambios = client.get("/api/admin/historial-precios", headers=a).json()["cambios"]
    assert [c["tipo"] for c in cambios] == ["ingrediente", "ingrediente", "producto"]
    assert cambios[-1]["nombre"] == "Mexicana" and cambios[-1]["usuario"] == "Administrador"
    assert len(client.get("/api/admin/historial-precios?tipo=producto", headers=a).json()["cambios"]) == 1
    assert client.get("/api/admin/historial-precios?tipo=x", headers=a).status_code == 400


def test_estadisticas_fecha(client, tokens):
    a = tokens["admin"]
    e = client.get("/api/admin/estadisticas?fecha=2020-01-01", headers=a).json()
    assert e == {"fecha": "2020-01-01", "ventas_dia": {"num_pedidos": 0, "total_ventas": 0.0},
                 "producto_mas_vendido": None}
    r = client.get("/api/admin/estadisticas?fecha=ayer", headers=a)
    assert r.status_code == 400 and codigo(r) == "FECHA_INVALIDA"


# ------------------------------------------------------------------ cobro, pendientes y gráficas
def test_cobro_y_pagados(client, tokens):
    h = tokens["recepcion"]
    p = client.post("/api/pedidos", json={"nombre_cliente": "Eva", "items": [{"producto_id": 8}]}).json()
    r = client.patch(f"/api/pedidos/{p['id']}/cobrar", headers=h)
    assert r.status_code == 200 and r.json()["pagado"] is True and r.json()["total"] == 20.0
    r = client.patch(f"/api/pedidos/{p['id']}/cobrar", headers=h)
    assert r.status_code == 409 and codigo(r) == "PEDIDO_YA_PAGADO"
    assert client.patch("/api/pedidos/999/cobrar", headers=h).status_code == 404
    pagados = client.get("/api/pedidos?pagado=true", headers=h).json()["pedidos"]
    assert len(pagados) == 1 and pagados[0]["pagado"] is True
    assert client.get("/api/pedidos?pagado=false", headers=h).json()["pedidos"] == []
    assert client.patch(f"/api/pedidos/{p['id']}/cobrar", headers=tokens["cocina"]).status_code == 403


def test_admin_consulta_pedidos_pendientes_y_espera(client, tokens):
    from app.config import MIN_POR_PIZZA
    assert client.get("/api/pedidos", headers=tokens["admin"]).status_code == 200
    p = client.post("/api/pedidos", json=PEDIDO_ANA).json()
    pend = client.get("/api/pedidos/pendientes", headers=tokens["recepcion"]).json()["pedidos"]
    assert [x["id"] for x in pend] == [p["id"]]
    est = client.get(f"/api/pedidos/{p['id']}/estado").json()
    assert est["espera_estimada_min"] == MIN_POR_PIZZA and est["pagado"] is False
    assert est["fecha_creacion"] and est["fecha_listo"] is None


def test_estadisticas_para_graficas(client, tokens):
    a, h = tokens["admin"], tokens["recepcion"]
    p = client.post("/api/pedidos", json={"nombre_cliente": "Eva", "items": [{"producto_id": 7, "cantidad": 2}]}).json()
    r = client.get("/api/admin/estadisticas/ventas-por-dia", headers=a).json()
    assert len(r["dias"]) == 7 and sum(d["total"] for d in r["dias"]) == 0  # sin cobrar no hay ventas
    client.patch(f"/api/pedidos/{p['id']}/cobrar", headers=h)
    r = client.get("/api/admin/estadisticas/ventas-por-dia", headers=a).json()
    assert sum(d["total"] for d in r["dias"]) == 50.0 and r["dias"][-1]["num_pedidos"] == 1
    r = client.get("/api/admin/estadisticas/productos-vendidos", headers=a).json()["productos"][0]
    assert r["nombre"] == "Refresco" and r["unidades"] == 2 and r["ingresos"] == 50.0
    horas = client.get("/api/admin/estadisticas/ventas-por-hora", headers=a).json()["horas"]
    assert len(horas) == 24 and sum(x["num_pedidos"] for x in horas) == 1
    e = client.get("/api/admin/estadisticas/pedidos-por-estado", headers=a).json()
    assert e["listo"] == 1 and e["pendiente"] == 0 and e["entregado"] == 0
    r = client.get("/api/admin/estadisticas/ventas-por-dia?desde=2026-02-01&hasta=2026-01-01", headers=a)
    assert r.status_code == 400 and codigo(r) == "RANGO_INVALIDO"
    assert client.get("/api/admin/estadisticas/ventas-por-dia", headers=h).status_code == 403
