#!/usr/bin/env python3
"""Pruebas de las órdenes ia, ia-profundo, ia-apagar e ia-estado.

Cada prueba abre ia en una terminal de verdad (un pty), igual que la Terminal de la Mac,
y comprueba que el motor se prende, se comparte y, sobre todo, que se apaga y suelta la
RAM al salir de cualquier forma: /exit, Ctrl+C, cerrando la ventana o matando ia.

Uso: python3 pruebas/probar_ordenes.py            (todas)
     python3 pruebas/probar_ordenes.py hup git      (las que contengan esas palabras)
Resultado en pantalla y en pruebas/RESULTADOS-ordenes.txt
"""
import fcntl
import json
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"
MOTOR = str(RAIZ / "motor" / "actual" / "llama-server")
PUERTO = 18080
CLAVE = (RAIZ / "estado" / "clave").read_text().strip()
RESULTADOS = []
TERMINALES = []   # las ventanas abiertas, para cerrarlas si una prueba falla a medias
os.environ["IA_AVISOS"] = "no"   # sin notificaciones de la Mac durante las pruebas


# ---------------------------------------------------------------- utilidades

def motores():
    """pids de llama-server de esta carpeta."""
    salida = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True, text=True).stdout
    vivos = []
    for linea in salida.splitlines():
        partes = linea.strip().split(None, 2)
        if len(partes) == 3 and partes[2].startswith(MOTOR):
            vivos.append((int(partes[0]), int(partes[1])))
    return vivos


def ram_motor_gb():
    m = motores()
    return round(m[0][1] / 1048576, 1) if m else 0.0


def esperar(cond, segundos, paso=0.5):
    fin = time.time() + segundos
    while time.time() < fin:
        if cond():
            return True
        time.sleep(paso)
    return cond()


def http(ruta, clave=CLAVE, metodo="GET", cabeceras=None, cuerpo=None):
    h = dict(cabeceras or {})
    if clave:
        h["Authorization"] = f"Bearer {clave}"
    req = urllib.request.Request(f"http://127.0.0.1:{PUERTO}{ruta}", method=metodo, headers=h,
                                 data=json.dumps(cuerpo).encode() if cuerpo else None)
    if cuerpo:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, dict(r.headers), r.read().decode(errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode(errors="ignore")
    except Exception as e:  # noqa: BLE001
        return 0, {}, str(e)


def sesiones():
    d = RAIZ / "estado" / "sesiones"
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


def orden(nombre, *args, cwd=None, env=None, timeout=900):
    r = subprocess.run([str(BIN / nombre), *args], cwd=cwd, env=env, capture_output=True,
                       text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout + r.stderr


class Terminal:
    """Una ventana de Terminal simulada con un pty: ia corre como si la abriera Gilberth."""

    def __init__(self, args, cwd, env=None):
        self.maestro, esclavo = pty.openpty()
        fcntl.ioctl(esclavo, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))

        def hacerla_su_terminal():
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        entorno = dict(os.environ if env is None else env)
        entorno["TERM"] = "xterm-256color"
        self.p = subprocess.Popen(args, cwd=cwd, env=entorno, stdin=esclavo, stdout=esclavo,
                                  stderr=esclavo, start_new_session=True,
                                  preexec_fn=hacerla_su_terminal, close_fds=True)
        os.close(esclavo)
        self.texto = b""
        self.cerrada = False
        self.hilo = threading.Thread(target=self._leer, daemon=True)
        self.hilo.start()
        TERMINALES.append(self)

    def _leer(self):
        # Con select y una espera corta: en macOS, cerrar el pty mientras otro hilo está
        # bloqueado leyéndolo deja el close() trabado para siempre.
        while not self.cerrada:
            try:
                if not select.select([self.maestro], [], [], 0.2)[0]:
                    continue
                d = os.read(self.maestro, 65536)
            except (OSError, ValueError):
                return
            if not d:
                return
            self.texto += d
            # prompt_toolkit pregunta dónde está el cursor; se le contesta como una terminal
            if b"\x1b[6n" in d:
                try:
                    os.write(self.maestro, b"\x1b[1;1R")
                except OSError:
                    return

    def ve(self, algo):
        return algo.encode() in self.texto

    def esperar_texto(self, algo, segundos):
        return esperar(lambda: self.ve(algo), segundos)

    def respuestas(self):
        """Cuántas respuestas lleva Aider: cada una termina con su línea «Tokens: …»."""
        return self.texto.count(b"Tokens: ")

    def preguntar(self, pregunta, segundos=300):
        """Escribe la pregunta y espera a que Aider termine de contestarla."""
        antes = self.respuestas()
        self.escribir(pregunta + "\r")
        return esperar(lambda: self.respuestas() > antes, segundos)

    def contestar_no(self, veces=3):
        """Si Aider se quedó preguntando algo «(Y)es/(N)o» (por ejemplo «Run shell command?»),
        contesta N, como haría una persona que no quiere ejecutar nada."""
        for _ in range(veces):
            time.sleep(3)
            if b"(Y)es/(N)o" not in self.texto[-400:]:
                return
            self.escribir("n\r")

    def escribir(self, s):
        os.write(self.maestro, s.encode() if isinstance(s, str) else s)

    def cerrar_ventana(self):
        """Como pulsar la X roja de la Terminal: el sistema manda SIGHUP."""
        if self.cerrada:
            return
        self.cerrada = True
        self.hilo.join(2)
        os.close(self.maestro)

    def esperar_fin(self, segundos):
        try:
            return self.p.wait(timeout=segundos)
        except subprocess.TimeoutExpired:
            return None

    def salida(self):
        return self.texto.decode(errors="ignore")


def abrir_ia(cwd, *extra, nombre="ia", env=None):
    t = Terminal([str(BIN / nombre), "--no-git", *extra] if "--git" not in extra
                 else [str(BIN / nombre), *[e for e in extra if e != "--git"]], cwd=cwd, env=env)
    lista = t.esperar_texto("Aider v0.86", 600)
    return t, lista


def prueba(nombre):
    def deco(f):
        f.nombre = nombre
        return f
    return deco


def anotar(nombre, ok, detalle):
    estado = "PASA " if ok else "FALLA"
    linea = f"{estado} {nombre}: {detalle}"
    print(linea, flush=True)
    RESULTADOS.append((ok, linea))


def limpiar():
    # primero las ventanas que haya dejado abiertas una prueba anterior
    for t in TERMINALES:
        if t.p.poll() is None:
            t.cerrar_ventana()
            if t.esperar_fin(30) is None:
                try:
                    os.killpg(t.p.pid, signal.SIGKILL)
                except OSError:
                    pass
        elif not t.cerrada:
            t.cerrar_ventana()
    TERMINALES.clear()
    orden("ia-apagar")
    esperar(lambda: not motores(), 30)


CARPETA = Path(tempfile.mkdtemp(prefix="ia-pruebas-"))


# ---------------------------------------------------------------- pruebas

@prueba("estado-apagada")
def p_estado_apagada():
    limpiar()
    c, s = orden("ia-estado")
    return c == 0 and "APAGADA" in s, s.splitlines()[0] if s else "sin salida"


@prueba("mensaje-y-apagado")
def p_mensaje():
    limpiar()
    d = CARPETA / "mensaje"
    d.mkdir()
    pico = [0.0]
    hilo_vivo = [True]

    def vigilar():
        while hilo_vivo[0]:
            pico[0] = max(pico[0], ram_motor_gb())
            time.sleep(1)

    h = threading.Thread(target=vigilar, daemon=True)
    h.start()
    t0 = time.time()
    c, s = orden("ia", "--no-git", "--yes-always", "--message",
                 "Responde solo con la palabra LISTO, en mayúsculas.", cwd=d)
    hilo_vivo[0] = False
    tarda = round(time.time() - t0)
    apagado = esperar(lambda: not motores(), 20)
    ok = c == 0 and "LISTO" in s and apagado and "RAM quedó libre" in s and not sesiones()
    return ok, f"código {c}, {tarda} s, RAM máxima del motor {pico[0]} GB, apagado al salir: {apagado}"


@prueba("estado-prendida")
def p_estado_prendida():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    c, s = orden("ia-estado")
    ok = lista and "PRENDIDA y lista" in s and "Sesiones de Aider abiertas: 1" in s
    t.escribir("/exit\r")
    fin = t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    linea = " | ".join(x.strip() for x in s.splitlines()[:3])
    return ok and fin is not None and apagado, f"{linea} | /exit apaga: {apagado}"


@prueba("salir-con-exit")
def p_exit():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    antes = ram_motor_gb()
    t.escribir("/exit\r")
    fin = t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return lista and fin is not None and apagado and not sesiones(), \
        f"RAM con la IA abierta {antes} GB; tras /exit motor apagado: {apagado}"


@prueba("salir-con-ctrl-c")
def p_ctrl_c():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    time.sleep(3)
    t.escribir(b"\x03")
    time.sleep(0.5)   # Aider se cierra si el segundo Ctrl+C llega antes de 2 s
    t.escribir(b"\x03")
    fin = t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return lista and fin is not None and apagado and not sesiones(), \
        f"dos Ctrl+C seguidos: Aider terminó ({fin is not None}), motor apagado: {apagado}"


@prueba("cerrar-la-ventana")
def p_hup():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    time.sleep(3)
    t.cerrar_ventana()
    fin = t.esperar_fin(60)
    t0 = time.time()
    apagado = esperar(lambda: not motores(), 40)
    return lista and apagado and not sesiones(), \
        f"ventana cerrada de golpe: motor apagado en {round(time.time() - t0)} s: {apagado}"


@prueba("cerrar-mientras-piensa")
def p_hup_pensando():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    t.escribir("Explica con mucho detalle, en 40 puntos, cómo funciona un árbol rojo-negro.\r")
    time.sleep(12)  # ya está generando
    t.cerrar_ventana()
    t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 40)
    return lista and apagado, f"cerrada en mitad de una respuesta: motor apagado: {apagado}"


@prueba("dos-ventanas")
def p_dos():
    limpiar()
    a, lista_a = abrir_ia(CARPETA)
    pid_a = [p for p, _ in motores()]
    b, lista_b = abrir_ia(CARPETA)
    pid_b = [p for p, _ in motores()]
    comparte = lista_b and b.ve("ya estaba prendida") and pid_a == pid_b and len(pid_b) == 1
    a.escribir("/exit\r")
    a.esperar_fin(60)
    time.sleep(3)
    sigue = len(motores()) == 1
    c, s = orden("ia-estado")
    una = "Sesiones de Aider abiertas: 1" in s
    b.escribir("/exit\r")
    b.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return lista_a and comparte and sigue and una and apagado, \
        f"la 2.ª usa el mismo motor: {comparte}; al cerrar la 1.ª sigue: {sigue}; al cerrar la 2.ª se apaga: {apagado}"


@prueba("profundo-y-normal-a-la-vez")
def p_modos():
    limpiar()
    a, la = abrir_ia(CARPETA)
    b, lb = abrir_ia(CARPETA, nombre="ia-profundo")
    ok = la and lb and len(motores()) == 1 and b.ve("qwen3.8-profundo") and a.ve("qwen3.8-normal")
    a.escribir("/exit\r")
    b.escribir("/exit\r")
    a.esperar_fin(60)
    b.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return ok and apagado, f"ia e ia-profundo comparten un solo motor: {ok}; apagado al final: {apagado}"


@prueba("matar-ia-de-golpe")
def p_kill9():
    limpiar()
    env = dict(os.environ, IA_VIGIA_INTERVALO="3")
    t, lista = abrir_ia(CARPETA, env=env)
    os.kill(t.p.pid, signal.SIGKILL)       # ia muere sin poder limpiar
    t.cerrar_ventana()                      # y Aider se queda sin terminal
    t0 = time.time()
    apagado = esperar(lambda: not motores(), 40)
    return lista and apagado, f"kill -9 a ia: el vigía apagó el motor en {round(time.time() - t0)} s: {apagado}"


@prueba("ia-apagar")
def p_apagar():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    c, s = orden("ia-apagar")
    apagado = esperar(lambda: not motores(), 10)
    t.escribir("/exit\r")
    fin = t.esperar_fin(60)
    c2, s2 = orden("ia-estado")
    return lista and c == 0 and apagado and fin is not None and "APAGADA" in s2, \
        f"{s.strip().splitlines()[0]} | luego /exit sin errores: {fin is not None}"


@prueba("puerto-ocupado")
def p_puerto():
    limpiar()
    otro = subprocess.Popen([sys.executable, "-m", "http.server", str(PUERTO), "--bind", "127.0.0.1"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    c, s = orden("ia", "--no-git", "--message", "hola", cwd=CARPETA, timeout=60)
    otro.terminate()
    otro.wait()
    ok = c == 1 and "lo está usando otro programa" in s and not motores()
    return ok, s.strip().splitlines()[0] if s.strip() else "sin salida"


@prueba("modelo-a-medio-bajar")
def p_modelo_incompleto():
    limpiar()
    falsa = CARPETA / "instalacion-falsa"
    shutil.copytree(RAIZ, falsa, ignore=shutil.ignore_patterns("modelos", "motor", "pruebas", ".git", "logs"),
                    symlinks=True)
    (falsa / "modelos").mkdir()
    (falsa / "motor").symlink_to(RAIZ / "motor")
    with open(falsa / "modelos" / "Qwen3.8-27B-Q8_0.gguf", "wb") as f:
        f.truncate(1024 * 1024)
    shutil.copy(RAIZ / "modelos" / "Qwen3.8-27B-Q8_0.gguf.sha256-esperado", falsa / "modelos")
    for sub in ("sesiones",):
        (falsa / "estado" / sub).mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(falsa / "bin" / "ia"), "--no-git", "--message", "hola"], cwd=CARPETA,
                       capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    s = r.stdout + r.stderr
    return r.returncode == 1 and "a medio bajar" in s and not motores(), s.strip().splitlines()[0]


@prueba("seguridad")
def p_seguridad():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    sin, _, _ = http("/v1/models", clave=None)
    mala, _, _ = http("/v1/models", clave="clave-falsa")
    buena, _, _ = http("/v1/models")
    raiz, _, _ = http("/", clave=None)
    slots, _, _ = http("/slots")
    _, cab, _ = http("/v1/models", metodo="OPTIONS", clave=None,
                     cabeceras={"Origin": "https://pagina-mala.example", "Access-Control-Request-Method": "POST"})
    cors = cab.get("Access-Control-Allow-Origin", "")
    escucha = subprocess.run(["lsof", "-nP", f"-iTCP:{PUERTO}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
    solo_local = "127.0.0.1:%d" % PUERTO in escucha and "*:%d" % PUERTO not in escucha
    t.escribir("/exit\r")
    t.esperar_fin(60)
    esperar(lambda: not motores(), 20)
    ok = lista and sin == 401 and mala == 401 and buena == 200 and raiz in (401, 404) and slots in (404, 501) \
        and cors in ("", f"http://127.0.0.1:{PUERTO}") and solo_local
    return ok, (f"sin clave {sin}, clave falsa {mala}, con clave {buena}, página de chat {raiz}, "
                f"/slots {slots}, CORS para otra web '{cors or 'ninguno'}', solo 127.0.0.1: {solo_local}")


@prueba("reposo-suelta-la-ram")
def p_reposo():
    limpiar()
    env = dict(os.environ, IA_REPOSO_SEGUNDOS="20")
    t, lista = abrir_ia(CARPETA, env=env)
    # primer pedido, y se espera a que termine de contestarlo
    t.preguntar("¿Cuánto es 17+25? Responde solo el número.")
    despierta = ram_motor_gb()
    time.sleep(35)   # el reposo empieza a los 20 s sin pedidos
    dormida = ram_motor_gb()
    c, s = orden("ia-estado")
    en_reposo = "EN REPOSO" in s
    desde = len(t.texto)
    contesta = t.preguntar("¿Cuánto es 30+31? Responde solo el número.") and b"61" in t.texto[desde:]
    otra_vez = ram_motor_gb()
    t.escribir("/exit\r")
    t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    ok = lista and en_reposo and dormida < despierta / 3 and contesta and otra_vez > dormida and apagado
    return ok, (f"despierta {despierta} GB, tras 20 s sin uso {dormida} GB ({'EN REPOSO' if en_reposo else 'no'}), "
                f"al pedirle algo vuelve ({otra_vez} GB) y contesta: {contesta}")


@prueba("carpeta-con-espacios-y-acentos")
def p_espacios():
    limpiar()
    d = CARPETA / "Deliservy - Código y Fuentes" / "año ñandú"
    d.mkdir(parents=True)
    (d / "saludo.py").write_text("def saludo():\n    return 'hola'\n")
    c, s = orden("ia", "--no-git", "--yes-always", "--message",
                 "Cambia saludo.py para que devuelva 'hola mundo'. Solo ese cambio.", "saludo.py", cwd=d)
    contenido = (d / "saludo.py").read_text()
    apagado = esperar(lambda: not motores(), 20)
    return c == 0 and "hola mundo" in contenido and apagado, f"código {c}; saludo.py cambiado: {'hola mundo' in contenido}"


@prueba("git-sin-commits-ni-gitignore")
def p_git():
    limpiar()
    d = CARPETA / "repo"
    d.mkdir()
    (d / "calc.py").write_text("def suma(a, b):\n    return a - b\n")
    (d / ".gitignore").write_text("secreto.txt\n")
    run = lambda *a: subprocess.run(["git", *a], cwd=d, capture_output=True, text=True).stdout  # noqa: E731
    run("init", "-q")
    run("add", "-A")
    run("-c", "user.email=prueba@local", "-c", "user.name=prueba", "commit", "-qm", "inicio")
    c, s = orden("ia", "--yes-always", "--message", "En calc.py, suma debe sumar. Arréglalo.", "calc.py", cwd=d)
    commits = run("rev-list", "--count", "HEAD").strip()
    gitignore = (d / ".gitignore").read_text()
    exclude = (d / ".git" / "info" / "exclude").read_text()
    estado = run("status", "--porcelain")
    arreglado = "a + b" in (d / "calc.py").read_text()
    apagado = esperar(lambda: not motores(), 20)
    ok = (c == 0 and arreglado and commits == "1" and gitignore == "secreto.txt\n" and ".aider*" in exclude
          and ".aider" not in estado and apagado)
    return ok, (f"arreglado: {arreglado}; commits: {commits} (no hizo ninguno); .gitignore intacto: "
                f"{gitignore == 'secreto.txt' + chr(10)}; git status: {estado.strip() or 'limpio'}")


@prueba("git-interactivo")
def p_git_interactivo():
    """El uso de todos los días: ia en un proyecto con git, se le pide un arreglo y se sale."""
    limpiar()
    d = CARPETA / "repo-interactivo"
    d.mkdir()
    (d / "precio.py").write_text("def con_iva(x):\n    return x * 1.6\n")
    (d / "test_precio.py").write_text("from precio import con_iva\n\n\ndef test_iva():\n"
                                      "    assert round(con_iva(100), 2) == 116.0\n")
    run = lambda *a: subprocess.run(["git", *a], cwd=d, capture_output=True, text=True).stdout  # noqa: E731
    run("init", "-q")
    run("add", "-A")
    run("-c", "user.email=prueba@local", "-c", "user.name=prueba", "commit", "-qm", "inicio")
    t, lista = abrir_ia(d, "--git", "precio.py", "--read", "test_precio.py")
    mapa = t.ve("Repo-map: using")
    contesta = t.preguntar("El IVA es del 16 %: con_iva multiplica mal. Arréglalo.")
    t.contestar_no()   # suele proponer ejecutar los tests: «Run shell command?»
    arreglado = "1.16" in (d / "precio.py").read_text()
    t.escribir("/exit\r")
    fin = t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    commits = run("rev-list", "--count", "HEAD").strip()
    estado = run("status", "--porcelain").strip()
    ok = lista and mapa and contesta and arreglado and fin is not None and apagado and commits == "1" \
        and ".aider" not in estado
    return ok, (f"con mapa del proyecto: {mapa}; arreglado: {arreglado}; commits: {commits}; "
                f"git status: {estado or 'limpio'}; /exit apaga: {apagado}")


@prueba("un-ctrl-c-corta-la-respuesta-y-sigue")
def p_ctrl_c_una_vez():
    limpiar()
    t, lista = abrir_ia(CARPETA)
    pid = [p for p, _ in motores()]
    t.escribir("Escribe una lista de 60 consejos de programación, numerados.\r")
    time.sleep(15)                      # ya está pensando o escribiendo
    t.escribir(b"\x03")                 # un solo Ctrl+C: cortar la respuesta
    time.sleep(4)
    motor_vivo = [p for p, _ in motores()] == pid and len(pid) == 1
    aider_vivo = t.p.poll() is None
    desde = len(t.texto)
    contesta = t.preguntar("¿Cuánto es 2+3? Responde solo el número.") and b"5" in t.texto[desde:]
    t.escribir("/exit\r")
    t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return lista and motor_vivo and aider_vivo and contesta and apagado, \
        (f"tras un Ctrl+C: motor sigue {motor_vivo}, Aider sigue {aider_vivo}, contesta la siguiente "
         f"pregunta {contesta}; al salir se apaga {apagado}")


@prueba("cerrar-la-ventana-con-zsh")
def p_zsh():
    """Como en la Terminal de verdad: zsh abre ia, y se cierra la ventana."""
    limpiar()
    t = Terminal(["/bin/zsh", "-i"], cwd=CARPETA)
    time.sleep(3)
    t.escribir(f"'{BIN / 'ia'}' --no-git\r")
    lista = t.esperar_texto("Aider v0.86", 600)
    time.sleep(3)
    t.cerrar_ventana()
    t0 = time.time()
    apagado = esperar(lambda: not motores(), 60)
    tarda = round(time.time() - t0)
    # en menos de 20 s lo apagó ia al salir; más tarde habría sido el vigía (30-45 s)
    return lista and apagado and tarda <= 20 and not sesiones(), \
        f"motor apagado {tarda} s después de cerrar la ventana (lo apagó {'ia al salir' if tarda <= 20 else 'el vigía'})"


@prueba("ctrl-c-mientras-carga")
def p_ctrl_c_cargando():
    limpiar()
    t = Terminal([str(BIN / "ia"), "--no-git"], cwd=CARPETA)
    vio = t.esperar_texto("Cargando el modelo", 60)
    t.escribir(b"\x03")
    fin = t.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 25)
    return vio and fin is not None and apagado and not sesiones(), \
        f"Ctrl+C mientras cargaba: ia terminó ({fin}), motor apagado {apagado}"


@prueba("segunda-ventana-con-la-ia-en-reposo")
def p_reposo_segunda():
    limpiar()
    env = dict(os.environ, IA_REPOSO_SEGUNDOS="15")
    a, la = abrir_ia(CARPETA, env=env)
    a.preguntar("¿Cuánto es 17+25? Responde solo el número.")
    time.sleep(25)   # el reposo empieza a los 15 s sin pedidos
    c, s = orden("ia-estado")
    dormida = "EN REPOSO" in s
    t0 = time.time()
    b, lb = abrir_ia(CARPETA, env=env)
    abre = round(time.time() - t0)
    desde = len(b.texto)
    contesta = b.preguntar("¿Cuánto es 30+31? Responde solo el número.") and b"61" in b.texto[desde:]
    a.escribir("/exit\r")
    b.escribir("/exit\r")
    a.esperar_fin(60)
    b.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return la and dormida and lb and abre < 60 and contesta and apagado, \
        f"en reposo: {dormida}; la 2.ª ventana abrió en {abre} s y contestó: {contesta}; apagado al final {apagado}"


@prueba("proyecto-con-su-propio-env")
def p_env():
    limpiar()
    d = CARPETA / "con-env"
    d.mkdir()
    (d / ".env").write_text("OPENAI_API_KEY=sk-de-otro-servicio\nOPENAI_API_BASE=http://127.0.0.1:9/v1\n")
    c, s = orden("ia", "--no-git", "--yes-always", "--message",
                 "Responde solo con la palabra LISTO, en mayúsculas.", cwd=d)
    apagado = esperar(lambda: not motores(), 20)
    return c == 0 and "LISTO" in s and apagado, f"con un .env que trae otra clave y otra dirección: código {c}, contestó {'LISTO' in s}"


@prueba("otro-puerto-con-la-ia-ya-prendida")
def p_puerto_activo():
    limpiar()
    a, la = abrir_ia(CARPETA)
    env = dict(os.environ, IA_PUERTO="18081")
    c, s = orden("ia", "--no-git", "--yes-always", "--message", "Responde solo con la palabra LISTO.",
                 cwd=CARPETA, env=env, timeout=600)
    a.escribir("/exit\r")
    a.esperar_fin(60)
    apagado = esperar(lambda: not motores(), 20)
    return la and c == 0 and "LISTO" in s and apagado, f"usa el motor ya prendido aunque se pida otro puerto: {'LISTO' in s}"


# ---------------------------------------------------------------- correr

def main():
    filtros = sys.argv[1:]
    pruebas = [v for v in globals().values() if callable(v) and hasattr(v, "nombre")]
    if filtros:
        pruebas = [p for p in pruebas if any(f in p.nombre for f in filtros)]
    print(f"Carpeta temporal: {CARPETA}\n")
    for p in pruebas:
        t0 = time.time()
        try:
            ok, detalle = p()
        except Exception as e:  # noqa: BLE001
            ok, detalle = False, f"error en la prueba: {e!r}"
        anotar(p.nombre, ok, f"{detalle} [{round(time.time() - t0)} s]")
    limpiar()
    pasan = sum(1 for ok, _ in RESULTADOS if ok)
    resumen = f"\n{pasan} de {len(RESULTADOS)} pruebas pasan ({time.strftime('%Y-%m-%d %H:%M')})"
    print(resumen)
    with open(RAIZ / "pruebas" / "RESULTADOS-ordenes.txt", "a") as f:
        f.write("\n".join(l for _, l in RESULTADOS) + resumen + "\n\n")
    shutil.rmtree(CARPETA, ignore_errors=True)
    sys.exit(0 if pasan == len(RESULTADOS) else 1)


if __name__ == "__main__":
    main()
