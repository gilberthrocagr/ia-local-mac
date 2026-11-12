# IA local para programar — macOS

Una IA que escribe y arregla código **en tu Mac, sin internet y sin pagar nada**. Solo para
código: nada de imágenes, vídeo ni chat. Se usa desde la Terminal con [Aider](https://aider.chat).

> Para Mac con **Apple Silicon** (M1 o posterior) y 64 GB de RAM. ¿Tienes un PC con **Windows**
> y una GPU **NVIDIA**? La versión hermana está en
> [ia-local-all-in-one](https://github.com/gilberthrocagr/ia-local-all-in-one).

- **Modelo:** [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) (Alibaba, agosto de 2026,
  licencia Apache 2.0), versión Q8_0 de [bartowski](https://huggingface.co/bartowski/Qwen3.8-27B-GGUF)
  (29,1 GB). Es el modelo que más razona de los que caben en 64 GB.
- **Motor:** [llama.cpp](https://github.com/ggml-org/llama.cpp) oficial para Mac (b12292), en la GPU.
- **Programa:** Aider 0.86.2, en la Terminal.
- Probado en una MacBook Pro M1 Max (GPU de 24 núcleos, 64 GB) con macOS 27: 24 de 24 pruebas
  de las órdenes y 5 de 5 tareas de programación a la primera. Todo en
  [pruebas/RESULTADOS.md](pruebas/RESULTADOS.md).

## Cómo se usa

```bash
cd ~/la/carpeta/de/tu/proyecto
ia
```

Se carga el modelo (unos segundos) y se abre Aider. Le escribes en español lo que quieres y
cambia tus archivos. Para salir: `/exit`.

| Orden | Para qué |
|---|---|
| `ia` | El día a día: piensa lo justo y responde. |
| `ia-profundo` | Problemas difíciles: piensa a fondo antes de responder. Puede tardar varios minutos. |
| `ia-estado` | Dice si está prendida, cuánta RAM ocupa y cuántas ventanas la usan. |
| `ia-apagar` | La apaga a la fuerza si algo se quedó trabado. |

Lo que pongas después de `ia` va a Aider. Por ejemplo `ia tarifa.py` abre Aider con ese
archivo ya añadido. Dentro de Aider: `/add archivo` añade uno, `/run pytest` ejecuta algo y
le enseña el resultado, `/undo` deshace el último cambio y `/help` lo explica todo.

Dos consejos que salen de las pruebas:

- **Dale los tests para leer:** `ia tarifa.py --read test_tarifa.py` (o, dentro,
  `/read-only test_tarifa.py`). Así los tiene en cuenta y no los puede cambiar.
- Si después de proponer un cambio pregunta **«Add file to the chat?»** por un archivo que no
  hace falta (casi siempre el de tests), contesta **N**. Si contestas que sí, Aider descarta el
  cambio que acababa de proponer y se lo vuelve a pedir; a veces el modelo se lía y no lo repite.
- A veces propone ejecutar algo (**«Run shell command?»**, por ejemplo `pytest`). **Y** lo
  ejecuta y le enseña el resultado para que siga arreglando; **N** no ejecuta nada. Hasta que
  contestes no acepta otra cosa, ni `/exit`.

## La RAM

- **Abierta ocupa unos 34 GB** de los 64 (queda fijada en la RAM para que no se congele). Cerrada, **nada**.
- Se apaga sola al salir de Aider de cualquier forma: `/exit`, Ctrl+C dos veces seguidas, o cerrando la
  ventana de la Terminal. Si tienes dos ventanas con `ia`, las dos usan el mismo modelo (no
  ocupa el doble) y se apaga al cerrar la última.
- Si la dejas abierta **15 minutos sin pedirle nada**, suelta la RAM sola y vuelve a cargar el
  modelo (unos segundos) con tu siguiente pedido.
- Si algo falla y se queda prendida, un vigía la apaga en menos de un minuto. Y siempre está
  `ia-apagar`.
- Para verlo con tus ojos: Monitor de Actividad → Memoria.

## Lo que no hace

- **No guarda nada en git por su cuenta.** Tú decides qué se queda (`git diff`, `git commit`).
- No toca el `.gitignore` de tus proyectos. Sus archivos (`.aider*`) los esconde de git en
  `.git/info/exclude`, que es local y no se sube.
- No se conecta a internet: el motor solo escucha en `127.0.0.1`, con clave, y sin página de chat.

## Avisos

- **Va lenta comparada con una IA en la nube:** escribe de 14 a 24 tokens por segundo (un token
  es un trozo de palabra) y lee unos 100 por segundo. Antes de responder piensa. En las pruebas,
  un arreglo pequeño tardó 1 minuto y medio, uno con muchas reglas 7 y medio, y el problema más
  difícil con `ia-profundo` unos 8. Cuando termina, la Mac te avisa.
- **Revisa lo que hace.** Estos modelos a veces dicen que comprobaron algo que no comprobaron.
  Pídele que ejecute los tests (`/run pytest`) y míralos tú.
- Las cifras de calidad del modelo son del fabricante, no independientes.

## Instalar desde cero (otra Mac con Apple Silicon y 64 GB)

```bash
git clone https://github.com/gilberthrocagr/ia-local-mac.git ~/proyectos/ia-local-mac
~/proyectos/ia-local-mac/instalar.sh
```

Baja el motor y el modelo (~29 GB) comprobando sus huellas, instala Aider con
[uv](https://docs.astral.sh/uv/) (`brew install uv` si no lo tienes) y deja las órdenes en
`~/.local/bin`. Si la descarga se corta, vuelve a ejecutarlo y sigue donde iba.

## Ajustes

Están en [config.sh](config.sh), con lo medido al lado. Cualquiera se puede cambiar para una
sola vez poniéndolo delante de la orden, por ejemplo `IA_REPOSO_SEGUNDOS=60 ia`. Los de Aider
(cuánto piensa cada orden, el muestreo de la ficha oficial) están en [aider/ajustes.yml](aider/ajustes.yml).

## Pruebas

```bash
python3 pruebas/probar_ordenes.py   # las órdenes: prender, compartir, apagar, seguridad...
pruebas/probar-codigo.sh            # 5 tareas de programación con sus tests
pruebas/medir-velocidad.sh          # velocidad con distintos ajustes
```

## Licencias

Este repositorio: MIT. Lo que instala tiene la suya: llama.cpp (MIT), Qwen3.8-27B (Apache 2.0),
Aider (Apache 2.0).
