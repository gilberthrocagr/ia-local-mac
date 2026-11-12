import random
import time

from repartidores import asignar, minimo_repartidores


def es_valida(entregas, asignacion):
    por_repartidor = {}
    for (ini, fin), r in zip(entregas, asignacion):
        por_repartidor.setdefault(r, []).append((ini, fin))
    for lista in por_repartidor.values():
        lista.sort()
        for (a1, f1), (a2, f2) in zip(lista, lista[1:]):
            if a2 < f1:
                return False
    return True


def test_vacio():
    assert minimo_repartidores([]) == 0
    assert asignar([]) == []


def test_una_tras_otra_cabe_en_un_repartidor():
    e = [(600, 630), (630, 700), (700, 745)]
    assert minimo_repartidores(e) == 1
    assert asignar(e) == [0, 0, 0]


def test_solapadas():
    e = [(600, 700), (610, 620), (650, 720), (700, 710)]
    assert minimo_repartidores(e) == 2
    assert asignar(e) == [0, 1, 1, 0]


def test_desordenadas_y_empates_de_inicio():
    e = [(500, 560), (480, 520), (480, 500), (520, 540), (500, 510)]
    # por inicio: (480,520)->0, (480,500)->1, (500,560)->1, (500,510)->2, (520,540)->0
    assert asignar(e) == [1, 0, 1, 0, 2]
    assert minimo_repartidores(e) == 3


def test_el_libre_de_numero_mas_bajo():
    e = [(0, 10), (0, 20), (0, 30), (25, 40), (10, 15), (20, 50)]
    # (0,10)->0 (0,20)->1 (0,30)->2 (10,15)->0 (20,50)->0 (25,40)->1
    assert asignar(e) == [0, 1, 2, 1, 0, 0]
    assert minimo_repartidores(e) == 3


def test_aleatorio_contra_fuerza_bruta():
    rng = random.Random(1234)
    for _ in range(300):
        n = rng.randint(1, 12)
        e = []
        for _ in range(n):
            a = rng.randint(0, 50)
            e.append((a, a + rng.randint(1, 20)))
        puntos = sorted({x for par in e for x in par})
        maximo = max(sum(1 for a, f in e if a <= t < f) for t in puntos)
        asig = asignar(e)
        assert minimo_repartidores(e) == maximo
        assert max(asig) + 1 == maximo
        assert es_valida(e, asig)


def test_rapido_con_100000():
    rng = random.Random(99)
    e = []
    for _ in range(100_000):
        a = rng.randint(0, 1_440_000)
        e.append((a, a + rng.randint(1, 3_000)))
    t = time.perf_counter()
    asig = asignar(e)
    m = minimo_repartidores(e)
    tarda = time.perf_counter() - t
    assert max(asig) + 1 == m
    assert tarda < 1.5, f"tardó {tarda:.2f} s"
