# Funciones que comparten ia, ia-profundo, ia-apagar, ia-estado y el vigía.
# Escrito para el bash 3.2 que trae macOS (nada de arrays asociativos ni wait -n).
# Necesita que antes se haya cargado config.sh.

IA_SESIONES="$IA_ESTADO/sesiones"
IA_CANDADO="$IA_ESTADO/candado"
IA_PID_SERVIDOR="$IA_ESTADO/servidor.pid"
IA_PUERTO_SERVIDOR="$IA_ESTADO/servidor.puerto"
IA_PID_VIGIA="$IA_ESTADO/vigia.pid"

# Mensajes al usuario. Si la Terminal ya se cerró, no falla.
ia_aviso() { printf '%s\n' "$*" >&2 2>/dev/null || true; }

# curl siempre directo a este equipo, aunque haya un proxy configurado.
ia_curl() { curl --noproxy '*' "$@"; }

ia_preparar_carpetas() {
  mkdir -p "$IA_ESTADO" "$IA_SESIONES" "$IA_LOGS" 2>/dev/null
  chmod 700 "$IA_ESTADO" "$IA_LOGS" 2>/dev/null
}

# Hora de arranque de un proceso: junto con el pid lo identifica sin confusiones
# (un pid se puede reutilizar; pid + hora de arranque, no).
ia_arranque_de() { ps -p "$1" -o lstart= 2>/dev/null; }

# ¿Sigue vivo el proceso que dejó esta marca "pid|hora"? Un zombi (murió y su padre aún no
# lo recogió) cuenta como muerto.
ia_marca_viva() {
  local pid="${1%%|*}" hora="${1#*|}"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || return 1
  case "$(ps -p "$pid" -o stat= 2>/dev/null)" in Z*) return 1 ;; esac
  [ "$(ia_arranque_de "$pid")" = "$hora" ]
}

# ---------- candado: que dos órdenes no toquen el estado a la vez ----------

ia_candado_tomar() {
  local intentos=0 marca edad viejo
  while ! mkdir "$IA_CANDADO" 2>/dev/null; do
    marca=$(cat "$IA_CANDADO/dueno" 2>/dev/null)
    viejo=0
    if [ -n "$marca" ]; then
      ia_marca_viva "$marca" || viejo=1                    # su dueño murió sin soltarlo
    else
      edad=$(( $(date +%s) - $(stat -f %m "$IA_CANDADO" 2>/dev/null || date +%s) ))
      [ "$edad" -gt 10 ] && viejo=1                         # creado sin dueño hace rato
    fi
    if [ "$viejo" = 1 ]; then
      # mv es atómico: si dos lo ven viejo a la vez, solo uno lo quita
      mv "$IA_CANDADO" "$IA_CANDADO.viejo.$$" 2>/dev/null && rm -rf "$IA_CANDADO.viejo.$$"
      continue
    fi
    intentos=$((intentos + 1))
    if [ "$intentos" -ge 300 ]; then  # 30 s
      ia_aviso "Otra orden ia está ocupada desde hace 30 s. Si se quedó trabada: ia-apagar"
      return 1
    fi
    sleep 0.1
  done
  echo "$$|$(ia_arranque_de $$)" > "$IA_CANDADO/dueno"
}

ia_candado_soltar() {
  local marca
  marca=$(cat "$IA_CANDADO/dueno" 2>/dev/null)
  [ "${marca%%|*}" = "$$" ] && rm -rf "$IA_CANDADO"
  return 0
}

# ---------- el motor ----------

ia_pid_servidor() { cat "$IA_PID_SERVIDOR" 2>/dev/null; }

# ¿El pid es un llama-server de esta carpeta? (protege de pids reutilizados)
ia_es_nuestro_motor() {
  local cmd
  [ -n "$1" ] || return 1
  cmd=$(ps -p "$1" -o command= 2>/dev/null) || return 1
  case "$cmd" in "$IA_MOTOR"*) return 0 ;; esac
  return 1
}

ia_servidor_vivo() { ia_es_nuestro_motor "$(ia_pid_servidor)"; }

# Todos los llama-server de esta carpeta, estén o no en el pid guardado.
ia_motores_vivos() {
  ps -axo pid=,command= 2>/dev/null | while read -r pid cmd; do
    case "$cmd" in "$IA_MOTOR"*) echo "$pid" ;; esac
  done
}

# El puerto del motor que está prendido (puede no ser IA_PUERTO si se cambió por una vez).
ia_puerto_activo() {
  local p
  p=$(cat "$IA_PUERTO_SERVIDOR" 2>/dev/null)
  echo "${p:-$IA_PUERTO}"
}

ia_url() { echo "http://$IA_HOST:$(ia_puerto_activo)$1"; }

ia_puerto_ocupado_por() {
  lsof -nP -iTCP:"$IA_PUERTO" -sTCP:LISTEN -t 2>/dev/null | head -1
}

ia_ram_libre_gb() {
  local tam
  tam=$(pagesize 2>/dev/null || echo 16384)
  vm_stat 2>/dev/null | awk -v ps="$tam" '
    /Pages free/        {f=$3}
    /Pages inactive/    {i=$3}
    /Pages speculative/ {s=$3}
    /Pages purgeable/   {p=$3}
    END {printf "%d", (f+i+s+p)*ps/1073741824}'
}

ia_rotar_log() {
  local f="$1"
  if [ -f "$f" ] && [ "$(stat -f %z "$f" 2>/dev/null || echo 0)" -gt 20000000 ]; then
    mv -f "$f" "$f.1"
  fi
}

ia_vigia_vivo() {
  local v
  v=$(cat "$IA_PID_VIGIA" 2>/dev/null)
  [ -n "$v" ] || return 1
  case "$(ps -p "$v" -o command= 2>/dev/null)" in *lib/vigia.sh*) return 0 ;; esac
  return 1
}

# Lanza el vigía del motor $1 en su propio grupo de procesos.
ia_vigia_lanzar() {
  ia_rotar_log "$IA_LOGS/vigia.log"
  set -m   # grupo propio: el Ctrl+C / Ctrl+Z de la ventana no le llega
  nohup /bin/bash "$IA_RAIZ/lib/vigia.sh" "$1" >> "$IA_LOGS/vigia.log" 2>&1 < /dev/null &
  echo $! > "$IA_PID_VIGIA"
  set +m
}

ia_servidor_arrancar() {
  local args pid
  ia_rotar_log "$IA_LOGS/servidor.log"
  args=( -m "$IA_MODELO" -a qwen3.8
         --host "$IA_HOST" --port "$IA_PUERTO"
         -c "$IA_CONTEXTO" -np 1 -ngl 99 -fa on
         --load-mode mmap+mlock
         -ctk "$IA_CACHE_K" -ctv "$IA_CACHE_V"
         -b 2048 -ub "$IA_UBATCH"
         --jinja --reasoning-budget -1
         --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0
         --no-webui --no-slots
         --api-key-file "$IA_CLAVE"
         --cors-origins "http://$IA_HOST:$IA_PUERTO"
         --sleep-idle-seconds "$IA_REPOSO_SEGUNDOS" )
  if [ "$IA_MTP" = "si" ]; then
    args=( "${args[@]}" --spec-type draft-mtp --spec-draft-n-max "$IA_MTP_N" )
  fi
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') arranca el motor (pedido por la sesión $$)" >> "$IA_LOGS/servidor.log"
  # --load-mode mmap+mlock: el archivo del modelo se mapea (sin copiarlo) y se fija en la RAM.
  # Sin fijarlo, macOS le quita trozos para otras apps y el motor se congela minutos
  # releyéndolos del disco (medido: pausas de 3 a 16 min). Con 'mlock' a secas lo copia
  # entero (dos veces 29 GB por un momento) y la carga llegó a 15 min. Al cerrar se suelta.
  # set -m: grupo de procesos propio, para que un Ctrl+C en Aider (que es para cortar una
  # respuesta) no le llegue al motor. nohup: que cerrar la Terminal no lo mate de golpe;
  # lo apagan terminar() o el vigía.
  set -m
  nohup "$IA_MOTOR" "${args[@]}" >> "$IA_LOGS/servidor.log" 2>&1 < /dev/null &
  pid=$!
  set +m
  echo "$pid" > "$IA_PID_SERVIDOR"
  echo "$IA_PUERTO" > "$IA_PUERTO_SERVIDOR"
  ia_vigia_lanzar "$pid"
}

# Para un motor: primero con cortesía, a los 15 s a la fuerza.
ia_parar_pid() {
  local pid="$1" i
  ia_es_nuestro_motor "$pid" || return 0
  kill -TERM "$pid" 2>/dev/null
  for i in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 0.5
  done
  kill -KILL "$pid" 2>/dev/null
  sleep 0.5
}

ia_servidor_parar() {
  local p
  p=$(ia_pid_servidor)
  ia_parar_pid "$p"
  if ! ia_es_nuestro_motor "$p"; then
    rm -f "$IA_PID_SERVIDOR" "$IA_PUERTO_SERVIDOR"
  fi
}

# Apaga cualquier motor de esta carpeta que no sea el registrado (restos de un fallo).
ia_parar_huerfanos() {
  local p actual
  actual=$(ia_pid_servidor)
  for p in $(ia_motores_vivos); do
    if [ "$p" != "$actual" ] || ! ia_servidor_vivo; then
      ia_parar_pid "$p"
    fi
  done
}

# Espera a que el modelo esté cargado (/health = 200). Devuelve 1 si el motor muere.
ia_esperar_listo() {
  local pid codigo vueltas=0
  pid=$(ia_pid_servidor)
  while :; do
    codigo=$(ia_curl -s -o /dev/null -w '%{http_code}' -m 2 "$(ia_url /health)" 2>/dev/null)
    if [ "$codigo" = "200" ]; then
      [ "$vueltas" -gt 0 ] && ia_aviso " lista."
      return 0
    fi
    if ! ia_es_nuestro_motor "$pid"; then
      ia_aviso ""
      ia_aviso "El motor se cerró mientras cargaba. Últimas líneas de $IA_LOGS/servidor.log:"
      tail -15 "$IA_LOGS/servidor.log" >&2 2>/dev/null
      return 1
    fi
    vueltas=$((vueltas + 1))
    [ "$vueltas" -eq 1 ] && printf 'Cargando el modelo en la memoria' >&2 2>/dev/null
    [ $((vueltas % 4)) -eq 0 ] && printf '.' >&2 2>/dev/null
    if [ "$vueltas" -ge 1200 ]; then   # 10 min
      ia_aviso ""
      ia_aviso "El modelo no terminó de cargar en 10 minutos. Mira $IA_LOGS/servidor.log"
      return 1
    fi
    sleep 0.5
  done
}

# ---------- sesiones (cada ia abierta deja un archivo con su pid y su hora) ----------

ia_sesion_registrar() {
  mkdir -p "$IA_SESIONES"
  ia_arranque_de $$ > "$IA_SESIONES/$$"
}

ia_sesion_quitar() { rm -f "$IA_SESIONES/$$"; }

ia_sesion_viva() { ia_marca_viva "$1|$(cat "$IA_SESIONES/$1" 2>/dev/null)"; }

ia_sesiones_limpiar() {
  local f pid
  for f in "$IA_SESIONES"/*; do
    [ -e "$f" ] || continue
    pid=$(basename "$f")
    ia_sesion_viva "$pid" || rm -f "$f"
  done
}

ia_sesiones_contar() {
  local f n=0
  ia_sesiones_limpiar
  for f in "$IA_SESIONES"/*; do
    [ -e "$f" ] && n=$((n + 1))
  done
  echo "$n"
}

# ---------- instalación ----------

ia_comprobar_instalacion() {
  local ok=0 esperado tam
  if [ ! -x "$IA_MOTOR" ]; then
    ia_aviso "Falta el motor ($IA_MOTOR). Ejecuta: $IA_RAIZ/instalar.sh"; ok=1
  fi
  if [ ! -f "$IA_MODELO" ]; then
    ia_aviso "Falta el modelo ($IA_MODELO). Ejecuta: $IA_RAIZ/instalar.sh"; ok=1
  else
    esperado=$(awk '{print $2}' "$IA_MODELO.sha256-esperado" 2>/dev/null)
    tam=$(stat -f %z "$IA_MODELO" 2>/dev/null)
    if [ -n "$esperado" ] && [ "$tam" != "$esperado" ]; then
      ia_aviso "El modelo está a medio bajar ($tam de $esperado bytes). Ejecuta: $IA_RAIZ/instalar.sh"; ok=1
    elif [ ! -f "$IA_MODELO.verificado" ]; then
      ia_aviso "El modelo no tiene la huella comprobada. Ejecuta: $IA_RAIZ/instalar.sh"; ok=1
    fi
  fi
  if ! command -v aider >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/aider" ]; then
    ia_aviso "Falta Aider. Ejecuta: $IA_RAIZ/instalar.sh"; ok=1
  fi
  if [ ! -s "$IA_CLAVE" ]; then
    ia_preparar_carpetas
    ( umask 077; openssl rand -hex 24 > "$IA_CLAVE" ) || { ia_aviso "No pude crear la clave $IA_CLAVE"; ok=1; }
  fi
  return $ok
}

# Que los archivos de Aider (.aider*) no aparezcan como cambios en git. Va en
# .git/info/exclude, que es local y no se sube: el .gitignore del proyecto no se toca.
ia_esconder_aider_de_git() {
  local comun
  comun="$(git rev-parse --git-common-dir 2>/dev/null)" || return 0
  mkdir -p "$comun/info" 2>/dev/null
  if ! /usr/bin/grep -qxF '.aider*' "$comun/info/exclude" 2>/dev/null; then
    printf '\n# archivos de Aider (IA local)\n.aider*\n' >> "$comun/info/exclude" 2>/dev/null
  fi
}
