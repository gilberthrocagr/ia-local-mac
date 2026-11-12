from dataclasses import dataclass, field


@dataclass
class Producto:
    nombre: str
    precio: float
    cantidad: int = 1


@dataclass
class Pedido:
    id: int
    productos: list = field(default_factory=list)
    envio: float = 0.0
