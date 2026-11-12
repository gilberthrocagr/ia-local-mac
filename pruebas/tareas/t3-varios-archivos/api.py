from modelos import Pedido
from servicio import subtotal, total


def pedido_a_dict(pedido: Pedido) -> dict:
    return {
        "id": pedido.id,
        "productos": [
            {"nombre": p.nombre, "precio": p.precio, "cantidad": p.cantidad}
            for p in pedido.productos
        ],
        "subtotal": subtotal(pedido),
        "envio": pedido.envio,
        "total": total(pedido),
    }
