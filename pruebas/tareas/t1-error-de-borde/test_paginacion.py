import pytest

from paginacion import paginar, total_paginas

DATOS = list(range(1, 26))  # 25 elementos


def test_primera_pagina():
    assert paginar(DATOS, 1, 10) == list(range(1, 11))


def test_ultima_pagina_incompleta():
    assert paginar(DATOS, 3, 10) == [21, 22, 23, 24, 25]


def test_pagina_fuera_de_rango():
    assert paginar(DATOS, 4, 10) == []


def test_pagina_invalida():
    with pytest.raises(ValueError):
        paginar(DATOS, 0, 10)
    with pytest.raises(ValueError):
        paginar(DATOS, 1, 0)


def test_total_paginas_redondea_hacia_arriba():
    assert total_paginas(25, 10) == 3
    assert total_paginas(20, 10) == 2
    assert total_paginas(1, 10) == 1


def test_total_paginas_cero():
    assert total_paginas(0, 10) == 0


def test_recorre_todo_sin_perder_ni_repetir():
    vistos = []
    for p in range(1, total_paginas(len(DATOS), 7) + 1):
        vistos += paginar(DATOS, p, 7)
    assert vistos == DATOS
