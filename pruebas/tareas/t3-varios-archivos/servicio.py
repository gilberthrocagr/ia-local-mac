from modelos import Pedido


def subtotal(pedido: Pedido) -> float:
    return round(sum(p.precio * p.cantidad for p in pedido.productos), 2)


def total(pedido: Pedido) -> float:
    return round(subtotal(pedido) + pedido.envio, 2)
