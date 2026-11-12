def paginar(elementos, pagina, por_pagina=10):
    """Devuelve los elementos de la página pedida (la primera página es la 1).

    - Si pagina < 1 o por_pagina < 1: ValueError.
    - Una página más allá del final devuelve una lista vacía.
    """
    if pagina < 1 or por_pagina < 1:
        raise ValueError("pagina y por_pagina deben ser >= 1")
    inicio = pagina * por_pagina
    return elementos[inicio:inicio + por_pagina]


def total_paginas(n, por_pagina=10):
    """Cuántas páginas hacen falta para n elementos (0 elementos = 0 páginas)."""
    if por_pagina < 1:
        raise ValueError("por_pagina debe ser >= 1")
    return n // por_pagina
