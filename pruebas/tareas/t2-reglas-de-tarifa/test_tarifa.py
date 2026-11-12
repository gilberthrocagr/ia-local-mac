import pytest

from tarifa import calcular_tarifa


@pytest.mark.parametrize("km,hora,lluvia,esperado", [
    (0, 10, False, 2.00),
    (3, 10, False, 2.00),
    (3.1, 10, False, 2.50),
    (5, 10, False, 3.00),
    (5.2, 10, False, 3.50),
    (5, 12, False, 3.45),
    (5, 17, False, 3.00),
    (5, 18, False, 3.45),
    (5, 20, False, 3.45),
    (5, 21, False, 3.00),
    (2, 20, False, 2.30),
    (5.2, 18, False, 4.03),   # 3,50 x 1,15 = 4,025 -> 4,03
    (4, 13, False, 2.88),     # 2,50 x 1,15 = 2,875 -> 2,88
    (4, 13, True, 3.88),
    (5, 19, True, 4.45),
    (45, 10, False, 23.00),
    (45, 12, False, 25.00),
    (45, 10, True, 24.00),
    (46, 10, True, 24.50),
    (47, 10, True, 25.00),
    (48, 10, True, 25.00),
    (100, 10, False, 25.00),
])
def test_tarifas(km, hora, lluvia, esperado):
    assert calcular_tarifa(km, hora, lluvia) == esperado


def test_devuelve_float():
    assert isinstance(calcular_tarifa(5, 10), float)


@pytest.mark.parametrize("km,hora", [(-1, 10), (-0.1, 10), (5, 24), (5, -1), (5, 12.5)])
def test_datos_invalidos(km, hora):
    with pytest.raises(ValueError):
        calcular_tarifa(km, hora)
