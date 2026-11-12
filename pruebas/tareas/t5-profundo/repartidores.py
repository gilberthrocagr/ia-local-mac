def minimo_repartidores(entregas):
    """Mínimo de repartidores para cubrir todas las entregas.

    Cada entrega es una tupla (inicio, fin) en minutos del día, con inicio < fin.
    Un repartidor hace una sola entrega a la vez, y puede empezar otra en el mismo
    minuto en que termina la anterior (una que acaba a las 600 y otra que empieza a las
    600 caben en el mismo repartidor). Lista vacía: 0.
    """
    raise NotImplementedError


def asignar(entregas):
    """Qué repartidor hace cada entrega, usando el mínimo posible de repartidores.

    Devuelve una lista con el número de repartidor (0, 1, 2...) de cada entrega, en el
    mismo orden en que vienen las entregas.

    Regla para que la respuesta sea única: se recorren las entregas por hora de inicio
    (si dos empiezan a la vez, en el orden en que vienen). A cada una le toca el
    repartidor libre de número más bajo; si no hay ninguno libre, uno nuevo con el
    siguiente número.

    Tiene que ser rápido: con 100.000 entregas debe tardar bastante menos de 1 segundo.
    """
    raise NotImplementedError
