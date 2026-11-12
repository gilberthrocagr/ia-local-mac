#!/bin/bash
# Vigía del motor. Lo arranca ia junto con llama-server y vive mientras el motor viva.
# Cada 15 s mira si queda alguna sesión de ia abierta. Si dos veces seguidas no queda
# ninguna (por ejemplo, la Terminal se cerró de golpe o ia murió con kill -9), apaga el
# motor para soltar la RAM.
#
# Uso: vigia.sh <pid del llama-server que vigila>

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$RAIZ/config.sh"
source "$RAIZ/lib/comun.sh"

MOTOR_PID="$1"
INTERVALO="${IA_VIGIA_INTERVALO:-15}"
vacias=0

trap '' HUP INT TSTP   # no lo mata ni lo congela la Terminal

echo "$(date '+%Y-%m-%d %H:%M:%S') vigía $$ vigilando el motor $MOTOR_PID"
while :; do
  sleep "$INTERVALO"
  # El motor ya no existe: este vigía sobra.
  if ! ia_es_nuestro_motor "$MOTOR_PID"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') el motor $MOTOR_PID ya no está: el vigía $$ termina"
    exit 0
  fi
  ia_candado_tomar || continue
  # Hay otro motor registrado y este quedó suelto: nadie lo usa.
  if [ "$(ia_pid_servidor)" != "$MOTOR_PID" ]; then
    ia_parar_pid "$MOTOR_PID"
    ia_candado_soltar
    echo "$(date '+%Y-%m-%d %H:%M:%S') el motor $MOTOR_PID estaba suelto (registrado: $(ia_pid_servidor)): apagado"
    exit 0
  fi
  if [ "$(ia_sesiones_contar)" -eq 0 ]; then
    vacias=$((vacias + 1))
  else
    vacias=0
  fi
  if [ "$vacias" -ge 2 ]; then
    ia_servidor_parar
    if ia_es_nuestro_motor "$MOTOR_PID"; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') no pude apagar el motor $MOTOR_PID; lo intento otra vez"
      ia_candado_soltar
      continue
    fi
    rm -f "$IA_PID_VIGIA"
    ia_candado_soltar
    echo "$(date '+%Y-%m-%d %H:%M:%S') sin sesiones abiertas: motor $MOTOR_PID apagado, RAM liberada"
    exit 0
  fi
  ia_candado_soltar
done
