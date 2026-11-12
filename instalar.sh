#!/bin/bash
# instalar.sh  Monta la IA local para programar en una Mac con Apple Silicon.
# Sirve para instalar desde cero y para reparar: lo que ya está bien no lo vuelve a bajar.
#
#   1. Motor: llama.cpp oficial para macOS arm64 (con su huella comprobada)
#   2. Modelo: Qwen3.8-27B Q8_0 de bartowski (29,1 GB, con su huella comprobada)
#   3. Aider 0.86.2 con uv
#   4. La clave del motor y las órdenes ia, ia-profundo, ia-apagar, ia-estado en ~/.local/bin

set -e
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$RAIZ/config.sh"
source "$RAIZ/lib/comun.sh"

MOTOR_VERSION="b12292"
MOTOR_SHA256="94b860a529a64aecfe20c4b9ccb9ca6fb4cf9126b019f3380ee02d7951ca11ef"
MOTOR_URL="https://github.com/ggml-org/llama.cpp/releases/download/$MOTOR_VERSION/llama-$MOTOR_VERSION-bin-macos-arm64.tar.gz"
MODELO_URL="https://huggingface.co/bartowski/Qwen3.8-27B-GGUF/resolve/main/Qwen3.8-27B-Q8_0.gguf"
MODELO_SHA256="a830e736efa71ce29589ff20b8713333a427e0d46ab774723be23800ad54362d"
MODELO_BYTES=29116388960
AIDER_VERSION="0.86.2"

paso() { printf '\n== %s\n' "$*"; }

[ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] || { echo "Esto es para Mac con Apple Silicon."; exit 1; }
ia_preparar_carpetas
mkdir -p "$RAIZ/motor" "$RAIZ/modelos" "$HOME/.local/bin"

paso "1/4 Motor llama.cpp $MOTOR_VERSION"
if [ -x "$RAIZ/motor/llama-$MOTOR_VERSION/llama-server" ]; then
  echo "Ya está."
else
  TMP="$RAIZ/motor/llama-$MOTOR_VERSION.tar.gz"
  curl -L --fail -s -S -o "$TMP" "$MOTOR_URL"
  echo "$MOTOR_SHA256  $TMP" | shasum -a 256 -c -
  tar -xzf "$TMP" -C "$RAIZ/motor"
  rm -f "$TMP"
fi
ln -sfn "llama-$MOTOR_VERSION" "$RAIZ/motor/actual"
"$IA_MOTOR" --version 2>&1 | head -1

paso "2/4 Modelo Qwen3.8-27B Q8_0 (29,1 GB)"
echo "$MODELO_SHA256 $MODELO_BYTES" > "$IA_MODELO.sha256-esperado"
MARCA="$IA_MODELO.verificado"
if [ -f "$MARCA" ] && [ "$(stat -f %z "$IA_MODELO" 2>/dev/null)" = "$MODELO_BYTES" ]; then
  echo "Ya está (huella comprobada el $(cat "$MARCA"))."
else
  rm -f "$MARCA"
  if [ "$(stat -f %z "$IA_MODELO" 2>/dev/null || echo 0)" -gt "$MODELO_BYTES" ]; then
    mv -f "$IA_MODELO" "$IA_MODELO.corrupto"   # más grande de la cuenta: no se puede seguir
  fi
  until [ "$(stat -f %z "$IA_MODELO" 2>/dev/null || echo 0)" = "$MODELO_BYTES" ]; do
    echo "Bajando (si se corta, vuelve a ejecutar instalar.sh y sigue donde iba)..."
    curl -L --fail -C - --retry 5 --retry-delay 10 -# -o "$IA_MODELO" "$MODELO_URL" || sleep 10
  done
  echo "Comprobando la huella (1-2 min)..."
  if ! echo "$MODELO_SHA256  $IA_MODELO" | shasum -a 256 -c -; then
    mv -f "$IA_MODELO" "$IA_MODELO.corrupto"
    echo "El modelo bajó dañado (lo dejé como $IA_MODELO.corrupto). Vuelve a ejecutar instalar.sh"
    exit 1
  fi
  date '+%Y-%m-%d %H:%M' > "$MARCA"
fi

paso "3/4 Aider $AIDER_VERSION"
# aider/versiones.txt cambia lo que no funciona en macOS 27 (scipy). La prueba de que está
# bien: que Aider sea esa versión y que su scipy cargue (sin ella se cae en carpetas con git).
AIDER_PY="$HOME/.local/share/uv/tools/aider-chat/bin/python"
if command -v aider >/dev/null 2>&1 && aider --version 2>/dev/null | /usr/bin/grep -qF "$AIDER_VERSION" \
   && "$AIDER_PY" -c "import scipy.sparse.linalg" >/dev/null 2>&1; then
  echo "Ya está."
else
  command -v uv >/dev/null 2>&1 || { echo "Falta uv: instálalo con  brew install uv  y repite."; exit 1; }
  uv tool install --force --python 3.12 --overrides "$RAIZ/aider/versiones.txt" "aider-chat==$AIDER_VERSION"
  "$AIDER_PY" -c "import scipy.sparse.linalg" || { echo "Aider quedó instalado pero su scipy no carga."; exit 1; }
fi

paso "4/4 Clave y órdenes"
if [ ! -s "$IA_CLAVE" ]; then
  ( umask 077; openssl rand -hex 24 > "$IA_CLAVE" )
  echo "Clave nueva en $IA_CLAVE"
fi
for o in ia ia-profundo ia-apagar ia-estado; do
  ln -sfn "$RAIZ/bin/$o" "$HOME/.local/bin/$o"
  echo "  $HOME/.local/bin/$o"
done
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "Ojo: ~/.local/bin no está en tu PATH. Añade esta línea a ~/.zprofile:"
     echo '  export PATH="$HOME/.local/bin:$PATH"' ;;
esac

echo
echo "Listo. Abre la Terminal en tu proyecto y escribe: ia   (o ia-profundo para pensar a fondo)"
