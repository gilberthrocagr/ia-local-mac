# Ajustes de la IA local para programar (Mac con Apple Silicon).
# Lo cargan las órdenes de bin/. Cada ajuste se puede cambiar para una sola vez poniéndolo
# delante de la orden, por ejemplo:  IA_REPOSO_SEGUNDOS=60 ia
# Lo medido está en pruebas/RESULTADOS.md (MacBook Pro M1 Max, GPU de 24 núcleos, 64 GB).
# Cuánto piensa cada orden (ia / ia-profundo) se ajusta en aider/ajustes.yml.

IA_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

IA_MOTOR="$IA_RAIZ/motor/actual/llama-server"      # llama.cpp oficial (b12292)
IA_MODELO="$IA_RAIZ/modelos/Qwen3.8-27B-Q8_0.gguf"  # 29,1 GB, trae las capas MTP
IA_HOST="127.0.0.1"                                 # solo este equipo
IA_PUERTO="${IA_PUERTO:-18080}"
IA_CONTEXTO="${IA_CONTEXTO:-131072}"                # tokens que puede tener a la vista

IA_ESTADO="$IA_RAIZ/estado"                         # pid, sesiones abiertas y la clave
IA_LOGS="$IA_RAIZ/logs"
IA_CLAVE="$IA_ESTADO/clave"

# Velocidad (medido con el modelo fijado en la RAM, tokens por segundo al escribir código):
#   sin MTP 10,4 · MTP 3: 20-23 · MTP 4: 22-24 · MTP 5: 23,4 · MTP 6: 22,3
#   Leer un texto largo (12.000 tokens): 100-110 por segundo; lote 2048 no lo mejora.
IA_MTP="${IA_MTP:-si}"                  # adelanta palabras con las capas MTP del modelo
IA_MTP_N="${IA_MTP_N:-4}"               # cuántas adelanta
IA_UBATCH="${IA_UBATCH:-512}"           # tamaño de lote al leer textos largos
IA_CACHE_K="${IA_CACHE_K:-q8_0}"
IA_CACHE_V="${IA_CACHE_V:-q8_0}"

# Si nadie le pide nada en este tiempo, el motor suelta el modelo de la RAM y lo vuelve a
# cargar solo con el siguiente pedido.
IA_REPOSO_SEGUNDOS="${IA_REPOSO_SEGUNDOS:-900}"

# Memoria que necesita libre para ir bien (modelo + contexto), en GB. Medido: 33-35.
IA_RAM_NECESARIA="${IA_RAM_NECESARIA:-36}"
