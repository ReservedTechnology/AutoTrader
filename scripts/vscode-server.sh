#!/bin/bash

# Script para instalar y configurar VS Code Server
# Esto te permitirá usar VS Code desde el navegador

VSCODE_SERVER_DIR="$HOME/.vscode-server"
SERVER_IP="192.168.1.140"
PORT="8081"

install_vscode_server() {
    echo "📥 Descargando VS Code Server..."
    
    # Crear directorio si no existe
    mkdir -p "$VSCODE_SERVER_DIR"
    cd "$VSCODE_SERVER_DIR"
    
    # Descargar la última versión de code-server
    curl -fsSL https://code-server.dev/install.sh | sh
    
    echo "✅ VS Code Server instalado"
}

configure_vscode_server() {
    echo "⚙️ Configurando VS Code Server..."
    
    # Crear directorio de configuración
    mkdir -p "$HOME/.config/code-server"
    
    # Crear archivo de configuración
    cat > "$HOME/.config/code-server/config.yaml" << EOF
bind-addr: 0.0.0.0:$PORT
auth: password
password: devserver123
cert: false
EOF

    echo "✅ Configuración creada"
    echo "🔑 Password: devserver123"
}

start_vscode_server() {
    echo "🚀 Iniciando VS Code Server..."
    
    # Iniciar code-server en background
    nohup code-server --bind-addr=0.0.0.0:$PORT > /tmp/code-server.log 2>&1 &
    
    echo "✅ VS Code Server iniciado"
    echo "🌐 Accede desde tu laptop Windows en: http://$SERVER_IP:$PORT"
    echo "🔑 Password: devserver123"
    echo "📂 Workspace: /home/oscar/Documentos/reserved-ml"
}

stop_vscode_server() {
    echo "🛑 Deteniendo VS Code Server..."
    pkill -f code-server
    echo "✅ VS Code Server detenido"
}

status_vscode_server() {
    echo "=== Estado de VS Code Server ==="
    if pgrep -f code-server > /dev/null; then
        echo "✅ VS Code Server está CORRIENDO"
        echo "🌐 URL: http://$SERVER_IP:$PORT"
        echo "🔑 Password: devserver123"
        
        # Mostrar log reciente
        echo ""
        echo "📋 Log reciente:"
        tail -5 /tmp/code-server.log 2>/dev/null || echo "No hay logs disponibles"
    else
        echo "❌ VS Code Server NO está corriendo"
    fi
    
    echo ""
    echo "🔌 Puerto $PORT:"
    sudo netstat -tlnp | grep :$PORT || echo "Puerto $PORT no está en uso"
}

case "$1" in
    install)
        install_vscode_server
        configure_vscode_server
        ;;
    start)
        start_vscode_server
        ;;
    stop)
        stop_vscode_server
        ;;
    restart)
        stop_vscode_server
        sleep 2
        start_vscode_server
        ;;
    status)
        status_vscode_server
        ;;
    *)
        echo "🖥️  VS Code Server Manager"
        echo ""
        echo "Uso: $0 [comando]"
        echo ""
        echo "Comandos:"
        echo "  install  - Instalar y configurar VS Code Server"
        echo "  start    - Iniciar VS Code Server"
        echo "  stop     - Detener VS Code Server" 
        echo "  restart  - Reiniciar VS Code Server"
        echo "  status   - Mostrar estado actual"
        echo ""
        echo "Después de instalar y iniciar, podrás acceder a VS Code"
        echo "desde tu laptop Windows en: http://$SERVER_IP:$PORT"
        echo ""
        status_vscode_server
        ;;
esac
