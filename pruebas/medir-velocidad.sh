#!/bin/bash
# Prende el motor con distintos ajustes y mide cada uno con medir.py.
# Uso: pruebas/medir-velocidad.sh            (todas las variantes)
#      pruebas/medir-velocidad.sh B D        (solo esas)
# No usa ia: arranca llama-server directamente en el puerto de pruebas 18099, con el
# modo de carga que diga cada variante. Mientras mide, apunta la memoria cada 5 s en
# logs/memoria-VARIANTE.log (páginas leídas del disco y comprimidas).
# Resultado: pruebas/velocidad.jsonl (una línea por variante)

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$RAIZ/config.sh"
PUERTO=18099
CLAVE="$(cat "$IA_CLAVE")"
SALIDA="$RAIZ/pruebas/velocidad.jsonl"
mkdir -p "$IA_LOGS"

variante() {
  case "$1" in
    # A-H: el modelo copiado a la RAM y fijado (-lm mlock)
    A) echo "-lm mlock -ub 512  -ctk q8_0 -ctv q8_0" ;;
    B) echo "-lm mlock -ub 1024 -ctk q8_0 -ctv q8_0" ;;
    C) echo "-lm mlock -ub 2048 -ctk q8_0 -ctv q8_0" ;;
    D) echo "-lm mlock -ub 512  -ctk f16 -ctv f16" ;;
    E) echo "-lm mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 1" ;;
    F) echo "-lm mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 2" ;;
    G) echo "-lm mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 3" ;;
    H) echo "-lm mlock -ub 2048 -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 2" ;;
    # I-L: el archivo mapeado y fijado sin copiarlo (-lm mmap+mlock)
    I) echo "-lm mmap+mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 3" ;;
    J) echo "-lm mmap+mlock -ub 2048 -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 3" ;;
    K) echo "-lm mmap+mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 4" ;;
    L) echo "-lm mmap+mlock -ub 512  -ctk q8_0 -ctv q8_0" ;;
    M) echo "-lm mmap+mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 5" ;;
    N) echo "-lm mmap+mlock -ub 512  -ctk q8_0 -ctv q8_0 --spec-type draft-mtp --spec-draft-n-max 6" ;;
  esac
}

LISTA="${*:-A B C D E F G}"
for V in $LISTA; do
  ARGS="$(variante "$V")"
  [ -n "$ARGS" ] || { echo "variante $V no existe"; continue; }
  echo "== $V: $ARGS"
  T0=$(date +%s)
  ( while :; do echo "$(date +%T) $(vm_stat | awk -F: '/Pageins|occupied by compressor|wired down/{gsub(/[ .]/,"",$2); gsub(/ /,"_",$1); printf "%s=%s ", $1, $2}')"; sleep 5; done ) > "$IA_LOGS/memoria-$V.log" 2>&1 &
  VIGILA=$!
  # shellcheck disable=SC2086
  "$IA_MOTOR" -m "$IA_MODELO" -a qwen3.8 --host 127.0.0.1 --port $PUERTO \
    -c "$IA_CONTEXTO" -np 1 -ngl 99 -fa on -b 2048 $ARGS \
    --jinja --no-webui --api-key "$CLAVE" > "$IA_LOGS/velocidad-$V.log" 2>&1 &
  PID=$!
  until [ "$(curl -s -o /dev/null -w '%{http_code}' -m 2 http://127.0.0.1:$PUERTO/health)" = 200 ]; do
    kill -0 $PID 2>/dev/null || { kill $VIGILA 2>/dev/null; echo "  el motor murió: mira $IA_LOGS/velocidad-$V.log"; tail -5 "$IA_LOGS/velocidad-$V.log"; continue 2; }
    sleep 1
  done
  CARGA=$(( $(date +%s) - T0 ))
  RSS=$(ps -p $PID -o rss= | tr -d ' ')
  LINEA=$(python3 "$RAIZ/pruebas/medir.py" "http://127.0.0.1:$PUERTO" "$CLAVE" "$V: $ARGS")
  RSS2=$(ps -p $PID -o rss= | tr -d ' ')
  kill $PID; wait $PID 2>/dev/null
  kill $VIGILA 2>/dev/null; wait $VIGILA 2>/dev/null
  LINEA=$(echo "$LINEA" | python3 -c "import json,sys; d=json.load(sys.stdin); d['carga_s']=$CARGA; d['ram_gb']=round(max($RSS,$RSS2)/1048576,1); print(json.dumps(d,ensure_ascii=False))")
  echo "  $LINEA"
  echo "$LINEA" >> "$SALIDA"
done
