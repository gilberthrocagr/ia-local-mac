#!/usr/bin/env python3
"""Mide la velocidad del motor ya prendido: escribir, leer textos largos y la caché.

Uso: medir.py URL CLAVE ETIQUETA
Imprime una línea JSON con las cifras (tokens por segundo según el propio motor).
Solo usa la biblioteca estándar.
"""
import json
import pathlib
import sys
import time
import urllib.request

URL, CLAVE, ETIQUETA = sys.argv[1], sys.argv[2], sys.argv[3]
RAIZ = pathlib.Path(__file__).resolve().parent.parent


def pedir(mensajes, max_tokens, esfuerzo="none", **extra):
    cuerpo = {"model": "qwen3.8", "messages": mensajes, "max_tokens": max_tokens,
              "temperature": 0.7, "top_p": 0.8, "reasoning_effort": esfuerzo, **extra}
    req = urllib.request.Request(
        URL + "/v1/chat/completions", data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {CLAVE}"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    d["_segundos"] = round(time.time() - t, 1)
    return d


def texto_largo(caracteres=32000):
    trozos = []
    for p in sorted(RAIZ.glob("lib/*.sh")) + sorted(RAIZ.glob("bin/*")) + [RAIZ / "instalar.sh"]:
        if p.is_file() and not p.is_symlink():
            trozos.append(f"### {p.name}\n{p.read_text(errors='ignore')}")
    texto = "\n".join(trozos)
    while len(texto) < caracteres:
        texto += "\n" + texto
    return texto[:caracteres]


PEDIDO_CODIGO = ("Escribe en Python una clase ValidadorRIF que valide RIF venezolanos "
                 "(letra J, V, E, G o P, guion y 9 dígitos), con docstrings y 6 tests de pytest. "
                 "Solo el código.")

res = {"etiqueta": ETIQUETA}

pedir([{"role": "user", "content": "Di hola."}], 8)  # calentar

escribir = []
for _ in range(4):
    d = pedir([{"role": "user", "content": PEDIDO_CODIGO}], 250)
    escribir.append(d["timings"]["predicted_per_second"])
    if "draft_n" in d["timings"]:
        res["mtp_aceptados"] = f'{d["timings"].get("draft_n_accepted")}/{d["timings"].get("draft_n")}'
res["escribe_tok_s"] = round(sum(escribir) / len(escribir), 1)
res["escribe_cada_vez"] = [round(x, 1) for x in escribir]

largo = texto_largo()
d = pedir([{"role": "user", "content": largo + "\n\nResume en una línea qué hace este código."}], 30)
res["lee_tok_s"] = round(d["timings"]["prompt_per_second"], 1)
res["lee_tokens"] = d["timings"]["prompt_n"]
res["lee_segundos"] = d["_segundos"]

d = pedir([{"role": "user", "content": largo + "\n\nResume en una línea qué hace este código."}], 30)
res["cache_tokens_releidos"] = d["timings"]["prompt_n"]
res["cache_segundos"] = d["_segundos"]

print(json.dumps(res, ensure_ascii=False))
