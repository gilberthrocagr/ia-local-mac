#!/bin/bash
# Pone a la IA a resolver las tareas de pruebas/tareas/ con ia (t5 con ia-profundo) y
# comprueba el resultado con sus tests. Cada tarea va en una copia nueva con git, para
# ver además que Aider no hace commits ni toca el .gitignore ni los tests.
# Los tests se le dan solo para leer (--read), como se recomienda en el README. Si a la
# primera no pasan todos, se le da una vuelta más con la salida de los tests (lo mismo que
# hacer /run pytest en Aider).
#
# Uso: pruebas/probar-codigo.sh            (las cinco)
#      pruebas/probar-codigo.sh t2 t5      (solo esas)
# Resultado: pruebas/RESULTADOS-codigo.txt y, por tarea, aider.log en pruebas/trabajo/

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SALIDA="$RAIZ/pruebas/RESULTADOS-codigo.txt"
LOTE="$RAIZ/pruebas/trabajo/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOTE"
TOTAL=0; BIEN=0; A_LA_PRIMERA=0
export IA_AVISOS=no   # sin notificaciones de la Mac durante las pruebas

correr_tests() {   # imprime "pasan/total"
  if [ -f pedidos.test.js ]; then
    node --test 2>&1 | awk '/^ℹ pass/ {p=$3} /^ℹ tests/ {t=$3} END {printf "%d/%d", p, t}'
  else
    uv run -q --with pytest python -m pytest -q -p no:cacheprovider 2>&1 | tail -1 | \
      awk '{p=0; f=0; e=0; for (i=1;i<=NF;i++) {if ($(i+1) ~ /^passed/) p=$i; if ($(i+1) ~ /^failed/) f=$i; if ($(i+1) ~ /^error/) e=$i}; printf "%d/%d", p, p+f+e}'
  fi
}

for ORIGEN in "$RAIZ"/pruebas/tareas/*/; do
  NOMBRE="$(basename "$ORIGEN")"
  if [ $# -gt 0 ]; then
    QUIERO=0; for f in "$@"; do case "$NOMBRE" in "$f"*) QUIERO=1 ;; esac; done
    [ $QUIERO = 1 ] || continue
  fi
  D="$LOTE/$NOMBRE"
  cp -R "$ORIGEN" "$D"
  cd "$D" || exit 1
  printf 'secreto.txt\n' > .gitignore
  git init -q && git add -A && git -c user.email=prueba@local -c user.name=prueba commit -qm "punto de partida"

  ANTES="$(correr_tests)"
  ORDEN=ia; case "$NOMBRE" in t5-*) ORDEN=ia-profundo ;; esac
  ARCHIVOS=$(ls *.py *.js 2>/dev/null | /usr/bin/grep -v -E '^test_|\.test\.js$')
  LEER=$(ls test_*.py *.test.js 2>/dev/null | sed 's/^/--read /')
  echo "== $NOMBRE con $ORDEN (tests antes: $ANTES) — archivos: $(echo $ARCHIVOS)"
  T0=$(date +%s)
  # shellcheck disable=SC2086
  "$RAIZ/bin/$ORDEN" --yes-always --message "$(cat PEDIDO.txt)" $ARCHIVOS $LEER > aider.log 2>&1 < /dev/null
  CODIGO=$?
  SEG=$(( $(date +%s) - T0 ))
  DESPUES="$(correr_tests)"
  PRIMERA="$DESPUES"
  VUELTAS=1
  if [ "${DESPUES%/*}" != "${DESPUES#*/}" ] || [ "${DESPUES#*/}" = 0 ]; then
    if [ -f pedidos.test.js ]; then FALLOS="$(node --test 2>&1 | tail -40)"
    else FALLOS="$(uv run -q --with pytest python -m pytest -q -p no:cacheprovider 2>&1 | tail -40)"; fi
    T1=$(date +%s)
    # shellcheck disable=SC2086
    "$RAIZ/bin/$ORDEN" --yes-always --message "Ejecuté los tests y no pasan todos. Esta es la salida:

$FALLOS

Arréglalo sin cambiar los tests." $ARCHIVOS $LEER > aider-2.log 2>&1 < /dev/null
    CODIGO=$?
    SEG="$SEG+$(( $(date +%s) - T1 ))"
    DESPUES="$(correr_tests)"
    VUELTAS=2
  fi

  COMMITS=$(git rev-list --count HEAD)
  GITIGNORE_OK=$([ "$(cat .gitignore)" = "secreto.txt" ] && echo si || echo NO)
  TESTS_OK=$(git diff --quiet HEAD -- 'test_*' '*.test.js' && echo si || echo NO)
  SUCIO=$(git status --porcelain | /usr/bin/grep -c '\.aider')
  P=${DESPUES%/*}; T=${DESPUES#*/}
  OK=NO
  if [ "$CODIGO" = 0 ] && [ "$P" = "$T" ] && [ "$T" -gt 0 ] && [ "$COMMITS" = 1 ] && \
     [ "$GITIGNORE_OK" = si ] && [ "$TESTS_OK" = si ] && [ "$SUCIO" = 0 ]; then
    OK=si; BIEN=$((BIEN + 1))
    [ $VUELTAS = 1 ] && A_LA_PRIMERA=$((A_LA_PRIMERA + 1))
  fi
  TOTAL=$((TOTAL + 1))
  if [ $OK = si ] && [ $VUELTAS = 1 ]; then RES="PASA a la primera"
  elif [ $OK = si ]; then RES="PASA con una vuelta más"
  else RES="FALLA"; fi
  DETALLE="tests $ANTES -> $PRIMERA"; [ $VUELTAS = 2 ] && DETALLE="$DETALLE -> $DESPUES"
  LINEA="$RES $NOMBRE ($ORDEN): $DETALLE en ${SEG} s; código $CODIGO; commits $COMMITS; .gitignore intacto $GITIGNORE_OK; tests sin tocar $TESTS_OK; .aider en git status $SUCIO"
  echo "$LINEA"
  echo "$LINEA" >> "$SALIDA"
  cd "$RAIZ" || exit 1
done
echo "$BIEN de $TOTAL tareas resueltas, $A_LA_PRIMERA a la primera ($(date '+%Y-%m-%d %H:%M'))" | tee -a "$SALIDA"
echo >> "$SALIDA"
[ "$BIEN" = "$TOTAL" ]
