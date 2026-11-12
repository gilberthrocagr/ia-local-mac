# Resultados de las pruebas

MacBook Pro M1 Max (GPU de 24 núcleos, 64 GB), macOS 27.0.1, 11 de noviembre de 2026.
llama.cpp b12292, Qwen3.8-27B Q8_0 (bartowski), Aider 0.86.2.

## Velocidad

Medido con [medir-velocidad.sh](medir-velocidad.sh): cuatro veces 250 tokens de código, un
texto de 12.000 tokens leído de una vez y la misma lectura repetida (caché). Tokens por segundo
según el propio motor. Todas las líneas están en [velocidad.jsonl](velocidad.jsonl).

| Variante | Escribe | Lee | RAM |
|---|---|---|---|
| Sin MTP | 10,4 | 110 | 33 GB |
| MTP 3 | 20,1 · 22,9 | 82 · 92 | 33-35 GB |
| **MTP 4 (la elegida)** | **24,1 · 22,3** | **107 · 102** | **35 GB** |
| MTP 5 | 23,4 | 102 | 33 GB |
| MTP 6 | 22,3 | 102 | 34 GB |

- **MTP** = el modelo adelanta varias palabras con sus propias capas de predicción y luego las
  confirma. Duplica la velocidad al escribir sin cambiar lo que escribe. Acierta el 60-80 %.
- Un lote de 2048 al leer no mejora la lectura (92 frente a 102-110).
- La caché funciona: releer el mismo texto largo tarda 2-4 s en vez de 2 minutos.
- Carga del modelo: 4 s si macOS lo tiene en caché, unos 15 s si lo lee del disco.

### Lo que hubo que arreglar: las pausas

Las primeras medidas daban de 0,3 a 21 tokens por segundo con los mismos ajustes: el motor se
quedaba congelado entre 3 y 16 minutos. macOS le quitaba trozos del modelo de la RAM y los
volvía a leer del disco. Probado:

- Sin fijar en la RAM (lo normal, `mmap`): pausas de minutos.
- `--load-mode mlock` (copia el modelo a la RAM y lo fija): la carga llegó a 15 minutos y
  seguía habiendo pausas, porque por un momento hay dos copias de 29 GB.
- **`--load-mode mmap+mlock`** (fija el archivo sin copiarlo): ni una pausa en 7 variantes
  (28 tandas de escritura y 14 lecturas largas). Es el que usa `ia`. El registro de memoria
  (`logs/memoria-*.log`) confirma unos 35 GB fijados mientras está prendida.

## Las órdenes: 24 de 24

[probar_ordenes.py](probar_ordenes.py) abre `ia` en una terminal de verdad (un pty) y comprueba
que se prende, se comparte y, sobre todo, que se apaga y suelta la RAM salga como salga.
El registro de cada tanda está en [RESULTADOS-ordenes.txt](RESULTADOS-ordenes.txt).

- Apagada no ocupa nada; prendida, 32,8-33,6 GB.
- Se apaga al salir con `/exit`, con dos Ctrl+C seguidos, cerrando la ventana (también con
  zsh de por medio, como en la Terminal), cerrándola mientras responde y pulsando Ctrl+C
  mientras carga.
- Un solo Ctrl+C corta la respuesta, no apaga nada y la siguiente pregunta se contesta bien.
- Dos ventanas, o `ia` e `ia-profundo` a la vez, usan un solo motor; se apaga al cerrar la última.
- Si `ia` muere con `kill -9`, el vigía apaga el motor (6 s en la prueba, con el vigía cada 3 s;
  con el ajuste normal, menos de 45 s).
- `ia-apagar` la apaga aunque haya un Aider abierto, y ese Aider sale luego sin errores.
- Puerto ocupado por otro programa, o modelo a medio bajar: se niega con un mensaje claro.
- Seguridad: sin clave o con una falsa, 401; sin página de chat; sin `/slots`; solo escucha en
  `127.0.0.1`; una web de fuera no puede llamarlo (CORS).
- Reposo: tras el tiempo sin uso baja de 33,5 GB a 0,8 GB, y vuelve a cargar solo con el
  siguiente pedido (también si el pedido viene de una segunda ventana).
- Carpeta con espacios y acentos, y un proyecto con su propio `.env` con otra clave: funcionan.
- En un proyecto con git, con un pedido suelto (`--message`) y en una sesión normal con el mapa
  del proyecto: arregla el archivo, no hace commits, no toca el `.gitignore` y sus archivos
  `.aider*` no aparecen en `git status`.

### Fallos encontrados y arreglados por estas pruebas

- **Aider se caía en cualquier carpeta con git**: la scipy 1.15.3 que pide Aider 0.86.2 no
  carga en macOS 27 (`dlopen` de `_spropack`). `instalar.sh` pone scipy 1.16.3
  ([aider/versiones.txt](../aider/versiones.txt)) y comprueba que carga. Se probaron uno por
  uno los 366 binarios del entorno de Aider: todos cargan.
- Un `ia` muerto que su padre aún no ha recogido (zombi) contaba como sesión abierta y el vigía
  no apagaba el motor. Ahora cuenta como muerto.
- Varios fallos de la Terminal simulada de las pruebas (no de `ia`): cerrar el pty mientras otro
  hilo lo lee deja el `close()` trabado en macOS; el segundo Ctrl+C llegaba justo a los 2 s (Aider
  solo sale si es antes); esperar una palabra que ya estaba en lo escrito por la prueba; y
  escribir `/exit` mientras Aider esperaba un sí o un no a «Run shell command?».

## Programación: 5 de 5 a la primera

[probar-codigo.sh](probar-codigo.sh) le da a la IA cinco tareas ([tareas/](tareas/)), cada una en
una copia nueva con git, con un solo pedido (`--message`) y sin ayuda. Luego pasan los tests.
El registro de cada tanda está en [RESULTADOS-codigo.txt](RESULTADOS-codigo.txt).

| Tarea | Orden | Tests | Tiempo | Escribió |
|---|---|---|---|---|
| t1 · error de borde en una paginación | `ia` | 3/7 → 7/7 | 1 min 37 s | 1.100 tokens |
| t2 · tarifa con 7 reglas y redondeo exacto | `ia` | 0/28 → 28/28 | 7 min 31 s | 5.600 tokens |
| t3 · cupones repartidos en 3 archivos | `ia` | 0/1 → 10/10 | 3 min 41 s | 2.700 tokens |
| t4 · JavaScript (node --test) | `ia` | 1/4 → 4/4 | 1 min 25 s | 700 tokens |
| t5 · asignar repartidores (montículo, 100.000 pedidos en < 1,5 s) | `ia-profundo` | 0/7 → 7/7 | 8 min 19 s | 6.400 tokens |

En las cinco: ningún commit, el `.gitignore` y los tests sin tocar, y nada de `.aider*` en
`git status`. El tiempo incluye cargar el modelo y lo que piensa antes de escribir; pensando
escribe a unos 14-20 tokens por segundo (algo menos que con código, porque el MTP acierta menos).

### La primera tanda: 4 de 5, y por qué

En la primera tanda los tests no se le daban. t2 quedó en 27/28: calculó con `float` y
3,50 × 1,15 da 4,0249999…, que redondea a 4,02 en vez de 4,03 (es justo la trampa que busca el
test). Al darle la salida del test encontró el arreglo correcto (todo con `Decimal`), pero no se
aplicó, por una costumbre de Aider: si el modelo nombra un archivo que no está en el chat (aquí
el de tests) y se contesta «sí» a «Add file to the chat?», **Aider descarta el cambio** de esa
respuesta y le pide que lo repita, y el modelo se lió. Pasó en las cinco tareas; en cuatro lo
repitió bien.

Con los tests dados solo para leer (`--read`) Aider no pregunta nada, el modelo los tiene en
cuenta y las cinco salen a la primera. Por eso el README lo recomienda, y también contestar N
a esa pregunta cuando el archivo no hace falta.
