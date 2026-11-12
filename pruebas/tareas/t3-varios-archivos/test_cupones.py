import pytest

from api import pedido_a_dict
from modelos import Pedido, Producto
from servicio import CUPONES, descuento, total


def pedido(cupon=None):
    return Pedido(id=9, productos=[Producto("Pizza", 10.0, 2)], envio=3.0, cupon=cupon)


def test_cupones_disponibles():
    assert CUPONES == {"DELI10": 10, "BIENVENIDA": 25}


def test_sin_cupon_no_hay_descuento():
    assert descuento(pedido()) == 0
    assert total(pedido()) == 23.0


def test_el_descuento_es_sobre_el_subtotal_no_sobre_el_envio():
    assert descuento(pedido("DELI10")) == 2.0
    assert total(pedido("DELI10")) == 21.0
    assert descuento(pedido("BIENVENIDA")) == 5.0
    assert total(pedido("BIENVENIDA")) == 18.0


def test_el_cupon_no_distingue_mayusculas_ni_espacios():
    assert descuento(pedido("  deli10 ")) == 2.0


def test_cupon_desconocido():
    with pytest.raises(ValueError):
        total(pedido("GRATIS"))


def test_descuento_redondeado_a_centimos():
    p = Pedido(id=3, productos=[Producto("Café", 3.33, 1)], cupon="DELI10")
    assert descuento(p) == 0.33
    assert total(p) == 3.0


def test_api_incluye_cupon_y_descuento():
    d = pedido_a_dict(pedido("BIENVENIDA"))
    assert d["cupon"] == "BIENVENIDA"
    assert d["descuento"] == 5.0
    assert d["total"] == 18.0
    assert pedido_a_dict(pedido())["cupon"] is None
    assert pedido_a_dict(pedido())["descuento"] == 0
