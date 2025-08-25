#!/bin/bash

# Script para gestionar proyectos de desarrollo
# Uso: ./project-manager.sh [proyecto] [accion]

PROJECT_DIR="/home/oscar/Documentos/reserved-ml"
SERVER_IP="192.168.1.140"

show_projects() {
    echo "=== Proyectos Disponibles ==="
    for dir in "$PROJECT_DIR"/*; do
        if [ -d "$dir" ]; then
            project_name=$(basename "$dir")
            echo "📁 $project_name"
            
            # Detectar tipo de proyecto
            if [ -f "$dir/package.json" ]; then
                if grep -q "next" "$dir/package.json"; then
                    echo "   🔸 Next.js Project"
                elif grep -q "vite" "$dir/package.json"; then
                    echo "   🔸 Vite Project"
                else
                    echo "   🔸 Node.js Project"
                fi
            elif [ -f "$dir/requirements.txt" ] || [ -f "$dir/setup.py" ]; then
                echo "   🔸 Python Project"
            else
                echo "   🔸 General Project"
            fi
            
            # Mostrar URLs disponibles
            echo "   🌐 http://$SERVER_IP/projects/$project_name"
            echo ""
        fi
    done
}

start_project() {
    local project=$1
    local project_path="$PROJECT_DIR/$project"
    
    if [ ! -d "$project_path" ]; then
        echo "❌ Proyecto '$project' no encontrado"
        return 1
    fi
    
    echo "🚀 Iniciando proyecto: $project"
    cd "$project_path"
    
    if [ -f "package.json" ]; then
        # Proyecto Node.js
        echo "📦 Instalando dependencias..."
        if [ -f "pnpm-lock.yaml" ]; then
            pnpm install
        elif [ -f "yarn.lock" ]; then
            yarn install
        else
            npm install
        fi
        
        echo "🔥 Iniciando servidor de desarrollo..."
        if grep -q "next" package.json; then
            # Next.js
            echo "▶️ Iniciando Next.js en http://$SERVER_IP:3000"
            npm run dev -- -H 0.0.0.0 &
        elif grep -q "vite" package.json; then
            # Vite
            echo "▶️ Iniciando Vite en http://$SERVER_IP:5173"
            if [ -f "pnpm-lock.yaml" ]; then
                pnpm dev --host 0.0.0.0 &
            else
                npm run dev -- --host 0.0.0.0 &
            fi
        else
            # Genérico
            npm run dev &
        fi
        
    elif [ -f "requirements.txt" ]; then
        # Proyecto Python
        echo "🐍 Configurando entorno Python..."
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt
        
        if [ -f "manage.py" ]; then
            # Django
            echo "▶️ Iniciando Django en http://$SERVER_IP:8000"
            python manage.py runserver 0.0.0.0:8000 &
        elif [ -f "app.py" ] || [ -f "main.py" ]; then
            # Flask o FastAPI
            echo "▶️ Iniciando servidor Python"
            python app.py &
        fi
    fi
    
    echo "✅ Proyecto '$project' iniciado"
    echo "🌐 Accesible desde Windows en las URLs mostradas arriba"
}

stop_project() {
    local project=$1
    echo "🛑 Deteniendo procesos de desarrollo para: $project"
    
    # Matar procesos de desarrollo comunes
    pkill -f "next.*dev"
    pkill -f "vite.*dev" 
    pkill -f "npm.*dev"
    pkill -f "pnpm.*dev"
    pkill -f "python.*runserver"
    
    echo "✅ Procesos detenidos"
}

show_processes() {
    echo "=== Procesos de Desarrollo Activos ==="
    ps aux | grep -E "(next|vite|npm|pnpm|python).*dev" | grep -v grep || echo "No hay procesos de desarrollo activos"
    echo ""
    echo "=== Puertos en Uso ==="
    sudo netstat -tlnp | grep -E ":(3000|3001|5173|8000|8080)" | head -10
}

case "$1" in
    list|ls)
        show_projects
        ;;
    start)
        if [ -z "$2" ]; then
            echo "❌ Especifica un proyecto: $0 start [nombre-proyecto]"
            echo ""
            show_projects
        else
            start_project "$2"
        fi
        ;;
    stop)
        if [ -z "$2" ]; then
            stop_project "all"
        else
            stop_project "$2"
        fi
        ;;
    ps|processes)
        show_processes
        ;;
    *)
        echo "🛠️  Gestor de Proyectos de Desarrollo"
        echo ""
        echo "Uso: $0 [comando] [proyecto]"
        echo ""
        echo "Comandos:"
        echo "  list, ls          - Listar todos los proyectos disponibles"
        echo "  start [proyecto]  - Iniciar servidor de desarrollo del proyecto"
        echo "  stop [proyecto]   - Detener servidor del proyecto (o 'all' para todos)"
        echo "  ps, processes     - Mostrar procesos activos"
        echo ""
        echo "📦 Para agregar nuevos proyectos:"
        echo "  ./add-project.sh  - Script para dar de alta proyectos"
        echo ""
        echo "Ejemplos:"
        echo "  $0 list"
        echo "  $0 start TacoManager"
        echo "  $0 start MiCondo" 
        echo "  $0 stop TacoManager"
        echo "  ./add-project.sh template nextjs MiNuevoEcommerce"
        echo ""
        show_projects
        ;;
esac
