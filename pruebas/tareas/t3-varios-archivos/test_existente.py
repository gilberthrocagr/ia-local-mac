from api import pedido_a_dict
from modelos import Pedido, Producto
from servicio import subtotal, total


def pedido_ejemplo():
    return Pedido(id=7, productos=[Producto("Arepa", 2.5, 2), Producto("Jugo", 1.75)], envio=1.5)


def test_subtotal_y_total():
    p = pedido_ejemplo()
    assert subtotal(p) == 6.75
    assert total(p) == 8.25


def test_pedido_vacio():
    p = Pedido(id=1)
    assert subtotal(p) == 0
    assert total(p) == 0


def test_api_conserva_los_campos_de_siempre():
    d = pedido_a_dict(pedido_ejemplo())
    assert d["id"] == 7
    assert d["subtotal"] == 6.75
    assert d["envio"] == 1.5
    assert d["total"] == 8.25
    assert d["productos"][0] == {"nombre": "Arepa", "precio": 2.5, "cantidad": 2}
