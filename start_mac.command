#!/bin/bash
# Script para iniciar la app en macOS
cd "$(dirname "$0")"

echo "Iniciando Santa Fuerza App..."

# Verificar si existe el entorno virtual, si no, crearlo
if [ ! -d "venv" ]; then
    echo "Configurando entorno por primera vez (esto solo pasa una vez)..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Iniciar el servidor en segundo plano
python app.py &
SERVER_PID=$!

# Esperar 2 segundos para que el servidor inicie
sleep 2

# Abrir en el navegador por defecto
open "http://localhost:5000"

# Mantener la terminal abierta y esperar al proceso
echo "=================================================="
echo "Servidor corriendo en http://localhost:5000"
echo "Cierra esta ventana para detener la aplicación."
echo "=================================================="

wait $SERVER_PID
