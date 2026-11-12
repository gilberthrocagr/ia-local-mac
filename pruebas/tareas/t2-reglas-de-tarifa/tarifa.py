def calcular_tarifa(km, hora, lluvia=False):
    """Precio en dólares de un envío. Devuelve un float redondeado a 2 decimales.

    Reglas, en este orden:
    1. km < 0, o hora que no sea un entero de 0 a 23: ValueError.
    2. La base es 2,00 $ y cubre los primeros 3 km.
    3. Cada km (o fracción de km) después de los 3 primeros suma 0,50 $.
       Ejemplo: 3,1 km cobra 1 km extra; 5,2 km cobra 3 km extra.
    4. En hora pico (12, 13, 18, 19 y 20) el total hasta aquí se multiplica por 1,15.
    5. Si llueve, se suma 1,00 $ después de la hora pico.
    6. El precio nunca pasa de 25,00 $ (el tope se aplica al final, con la lluvia incluida).
    7. Se redondea a 2 decimales con la regla de la escuela: 4,025 -> 4,03 (mitad hacia arriba).
    """
    raise NotImplementedError
