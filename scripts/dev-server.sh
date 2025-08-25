#!/bin/bash

# Script de configuración del servidor de desarrollo
# Uso: ./dev-server.sh [start|stop|status|restart]

SERVER_IP="192.168.1.140"
PROJECT_DIR="/home/oscar/Documentos/reserved-ml"

show_status() {
    echo "=== Estado del Servidor de Desarrollo ==="
    echo "IP del servidor: $SERVER_IP"
    echo "Directorio de proyectos: $PROJECT_DIR"
    echo ""
    
    echo "SSH Server:"
    systemctl is-active ssh || echo "SSH no está corriendo"
    
    echo "Apache2 Server:"
    systemctl is-active apache2 || echo "Apache2 no está corriendo"
    
    echo "Docker Containers:"
    sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker no disponible"
    
    echo ""
    echo "Puertos en uso:"
    sudo netstat -tlnp | grep -E ":(22|80|3000|3001|5000|5173|8080|8081)" | head -10
}

start_server() {
    echo "Iniciando servidor de desarrollo..."
    
    # Asegurar que SSH esté corriendo
    sudo systemctl start ssh
    sudo systemctl enable ssh
    
    # Asegurar que Apache esté corriendo  
    sudo systemctl start apache2
    sudo systemctl enable apache2
    
    # Crear enlace simbólico para proyectos si no existe
    if [ ! -L "/var/www/html/projects" ]; then
        sudo ln -sf "$PROJECT_DIR" /var/www/html/projects
        echo "Enlace simbólico creado: http://$SERVER_IP/projects"
    fi
    
    # Configurar permisos
    sudo chown -R oscar:www-data "$PROJECT_DIR"
    sudo chmod -R 755 "$PROJECT_DIR"
    
    echo ""
    echo "=== Servidor de Desarrollo Listo ==="
    echo "Desde tu laptop Windows puedes:"
    echo "1. SSH: ssh oscar@$SERVER_IP"
    echo "2. Web: http://$SERVER_IP (Apache)"
    echo "3. Proyectos: http://$SERVER_IP/projects"
    echo "4. Docker API: http://$SERVER_IP:8080"
    echo ""
    show_status
}

stop_server() {
    echo "Deteniendo servicios opcionales..."
    # No detenemos SSH para mantener acceso remoto
    echo "SSH se mantiene activo para acceso remoto"
    echo "Apache se mantiene activo para servir archivos"
    echo "Para detener todo: sudo systemctl stop apache2 ssh"
}

restart_server() {
    echo "Reiniciando servicios..."
    sudo systemctl restart ssh apache2
    echo "Servicios reiniciados"
    show_status
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        show_status
        ;;
    restart)
        restart_server
        ;;
    *)
        echo "Uso: $0 {start|stop|status|restart}"
        echo ""
        echo "Comandos disponibles:"
        echo "  start   - Iniciar todos los servicios del servidor de desarrollo"
        echo "  stop    - Información sobre cómo detener servicios"
        echo "  status  - Mostrar estado actual de todos los servicios"
        echo "  restart - Reiniciar servicios principales"
        echo ""
        show_status
        ;;
esac
