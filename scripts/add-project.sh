#!/bin/bash

# Script para dar de alta nuevos proyectos en el servidor de desarrollo
# Uso: ./add-project.sh [comando] [opciones]

PROJECT_DIR="/home/oscar/Documentos/reserved-ml"
SERVER_IP="192.168.1.140"

show_help() {
    echo "📦 Gestor de Altas de Proyectos"
    echo ""
    echo "Uso: $0 [comando] [opciones]"
    echo ""
    echo "Comandos:"
    echo "  clone [url] [nombre]     - Clonar proyecto desde Git"
    echo "  copy [origen] [nombre]   - Copiar proyecto local existente"
    echo "  template [tipo] [nombre] - Crear proyecto desde plantilla"
    echo "  import [zip] [nombre]    - Importar proyecto desde ZIP"
    echo "  list-templates           - Mostrar plantillas disponibles"
    echo "  status [nombre]          - Ver estado de un proyecto"
    echo ""
    echo "Tipos de plantillas:"
    echo "  nextjs        - Proyecto Next.js con TypeScript"
    echo "  vite-react    - Proyecto Vite + React + TypeScript"
    echo "  vite-vue      - Proyecto Vite + Vue + TypeScript"
    echo "  node-express  - API Node.js + Express"
    echo "  python-flask  - API Python + Flask"
    echo "  python-django - Proyecto Django"
    echo "  static        - Sitio web estático"
    echo ""
    echo "Ejemplos:"
    echo "  $0 clone https://github.com/usuario/proyecto.git MiProyecto"
    echo "  $0 template nextjs NuevoEcommerce"
    echo "  $0 copy /ruta/proyecto ProyectoLocal"
    echo "  $0 import proyecto.zip ProyectoImportado"
}

clone_project() {
    local repo_url=$1
    local project_name=$2
    
    if [ -z "$repo_url" ] || [ -z "$project_name" ]; then
        echo "❌ Uso: $0 clone [url-repo] [nombre-proyecto]"
        return 1
    fi
    
    local project_path="$PROJECT_DIR/$project_name"
    
    if [ -d "$project_path" ]; then
        echo "❌ El proyecto '$project_name' ya existe"
        return 1
    fi
    
    echo "📥 Clonando repositorio: $repo_url"
    echo "📁 Destino: $project_path"
    
    cd "$PROJECT_DIR"
    if git clone "$repo_url" "$project_name"; then
        echo "✅ Proyecto clonado exitosamente"
        setup_project "$project_name"
    else
        echo "❌ Error al clonar el repositorio"
        return 1
    fi
}

copy_project() {
    local source_path=$1
    local project_name=$2
    
    if [ -z "$source_path" ] || [ -z "$project_name" ]; then
        echo "❌ Uso: $0 copy [ruta-origen] [nombre-proyecto]"
        return 1
    fi
    
    if [ ! -d "$source_path" ]; then
        echo "❌ El directorio origen '$source_path' no existe"
        return 1
    fi
    
    local project_path="$PROJECT_DIR/$project_name"
    
    if [ -d "$project_path" ]; then
        echo "❌ El proyecto '$project_name' ya existe"
        return 1
    fi
    
    echo "📋 Copiando proyecto desde: $source_path"
    echo "📁 Destino: $project_path"
    
    if cp -r "$source_path" "$project_path"; then
        echo "✅ Proyecto copiado exitosamente"
        setup_project "$project_name"
    else
        echo "❌ Error al copiar el proyecto"
        return 1
    fi
}

create_from_template() {
    local template_type=$1
    local project_name=$2
    
    if [ -z "$template_type" ] || [ -z "$project_name" ]; then
        echo "❌ Uso: $0 template [tipo] [nombre-proyecto]"
        echo "Ejecuta '$0 list-templates' para ver tipos disponibles"
        return 1
    fi
    
    local project_path="$PROJECT_DIR/$project_name"
    
    if [ -d "$project_path" ]; then
        echo "❌ El proyecto '$project_name' ya existe"
        return 1
    fi
    
    echo "🎨 Creando proyecto '$project_name' desde plantilla '$template_type'"
    mkdir -p "$project_path"
    cd "$project_path"
    
    case "$template_type" in
        nextjs)
            create_nextjs_template "$project_name"
            ;;
        vite-react)
            create_vite_react_template "$project_name"
            ;;
        vite-vue)
            create_vite_vue_template "$project_name"
            ;;
        node-express)
            create_node_express_template "$project_name"
            ;;
        python-flask)
            create_python_flask_template "$project_name"
            ;;
        python-django)
            create_python_django_template "$project_name"
            ;;
        static)
            create_static_template "$project_name"
            ;;
        *)
            echo "❌ Plantilla '$template_type' no reconocida"
            rmdir "$project_path"
            return 1
            ;;
    esac
    
    echo "✅ Proyecto creado exitosamente"
    setup_project "$project_name"
}

create_nextjs_template() {
    local project_name=$1
    echo "🚀 Creando proyecto Next.js..."
    npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
}

create_vite_react_template() {
    local project_name=$1
    echo "⚡ Creando proyecto Vite + React..."
    npm create vite@latest . -- --template react-ts
}

create_vite_vue_template() {
    local project_name=$1
    echo "⚡ Creando proyecto Vite + Vue..."
    npm create vite@latest . -- --template vue-ts
}

create_node_express_template() {
    local project_name=$1
    echo "🟢 Creando API Node.js + Express..."
    
    npm init -y
    npm install express cors helmet morgan dotenv
    npm install -D nodemon @types/node typescript ts-node
    
    # Crear estructura básica
    mkdir -p src routes middleware
    
    cat > src/app.ts << 'EOF'
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';

const app = express();
const PORT = process.env.PORT || 3000;

// Middlewares
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Rutas
app.get('/', (req, res) => {
  res.json({ message: 'API funcionando correctamente' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Servidor corriendo en http://0.0.0.0:${PORT}`);
});
EOF
    
    # Actualizar package.json
    npm pkg set scripts.dev="nodemon src/app.ts"
    npm pkg set scripts.build="tsc"
    npm pkg set scripts.start="node dist/app.js"
}

create_python_flask_template() {
    local project_name=$1
    echo "🐍 Creando API Python + Flask..."
    
    # Crear requirements.txt
    cat > requirements.txt << 'EOF'
Flask==2.3.3
Flask-CORS==4.0.0
python-dotenv==1.0.0
EOF
    
    # Crear app.py
    cat > app.py << 'EOF'
from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "API Python funcionando correctamente"})

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "project": "'"$project_name"'"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF
    
    # Crear .env
    echo "FLASK_ENV=development" > .env
}

create_python_django_template() {
    local project_name=$1
    echo "🎯 Creando proyecto Django..."
    
    pip install django
    django-admin startproject . .
}

create_static_template() {
    local project_name=$1
    echo "📄 Creando sitio web estático..."
    
    mkdir -p css js images
    
    cat > index.html << EOF
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$project_name</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>$project_name</h1>
    </header>
    <main>
        <p>¡Proyecto creado exitosamente!</p>
        <p>Edita este archivo para personalizar tu sitio.</p>
    </main>
    <script src="js/main.js"></script>
</body>
</html>
EOF

    cat > css/style.css << 'EOF'
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
    background-color: #f4f4f4;
}

header {
    background: #333;
    color: white;
    padding: 1rem;
    text-align: center;
    margin-bottom: 2rem;
}

main {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
EOF

    cat > js/main.js << 'EOF'
console.log('Proyecto estático cargado correctamente');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado');
});
EOF
}

import_project() {
    local zip_file=$1
    local project_name=$2
    
    if [ -z "$zip_file" ] || [ -z "$project_name" ]; then
        echo "❌ Uso: $0 import [archivo.zip] [nombre-proyecto]"
        return 1
    fi
    
    if [ ! -f "$zip_file" ]; then
        echo "❌ El archivo '$zip_file' no existe"
        return 1
    fi
    
    local project_path="$PROJECT_DIR/$project_name"
    
    if [ -d "$project_path" ]; then
        echo "❌ El proyecto '$project_name' ya existe"
        return 1
    fi
    
    echo "📦 Extrayendo proyecto desde: $zip_file"
    mkdir -p "$project_path"
    
    if unzip "$zip_file" -d "$project_path"; then
        echo "✅ Proyecto importado exitosamente"
        setup_project "$project_name"
    else
        echo "❌ Error al extraer el archivo ZIP"
        rmdir "$project_path"
        return 1
    fi
}

setup_project() {
    local project_name=$1
    local project_path="$PROJECT_DIR/$project_name"
    
    echo "⚙️ Configurando proyecto '$project_name'..."
    
    # Establecer permisos correctos
    chown -R oscar:www-data "$project_path"
    chmod -R 755 "$project_path"
    
    # Detectar tipo de proyecto e instalar dependencias
    cd "$project_path"
    
    if [ -f "package.json" ]; then
        echo "📦 Detectado proyecto Node.js, instalando dependencias..."
        if [ -f "pnpm-lock.yaml" ]; then
            pnpm install
        elif [ -f "yarn.lock" ]; then
            yarn install
        else
            npm install
        fi
    elif [ -f "requirements.txt" ]; then
        echo "🐍 Detectado proyecto Python, configurando entorno..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi
    
    # Crear archivo de configuración del proyecto
    cat > .dev-server.conf << EOF
PROJECT_NAME=$project_name
PROJECT_TYPE=$(detect_project_type "$project_path")
CREATED_DATE=$(date)
SERVER_IP=$SERVER_IP
EOF
    
    echo ""
    echo "✅ Proyecto '$project_name' configurado exitosamente"
    echo "🌐 Accesible en: http://$SERVER_IP/projects/$project_name"
    echo ""
    echo "Para iniciarlo:"
    echo "  ./project-manager.sh start $project_name"
    echo ""
    
    # Mostrar información del proyecto
    show_project_info "$project_name"
}

detect_project_type() {
    local project_path=$1
    
    if [ -f "$project_path/package.json" ]; then
        if grep -q "next" "$project_path/package.json"; then
            echo "nextjs"
        elif grep -q "vite" "$project_path/package.json"; then
            echo "vite"
        else
            echo "nodejs"
        fi
    elif [ -f "$project_path/requirements.txt" ]; then
        if [ -f "$project_path/manage.py" ]; then
            echo "django"
        else
            echo "python"
        fi
    elif [ -f "$project_path/index.html" ]; then
        echo "static"
    else
        echo "general"
    fi
}

show_project_info() {
    local project_name=$1
    local project_path="$PROJECT_DIR/$project_name"
    
    echo "📋 Información del Proyecto: $project_name"
    echo "📁 Ubicación: $project_path"
    echo "🔗 URL Web: http://$SERVER_IP/projects/$project_name"
    
    local project_type=$(detect_project_type "$project_path")
    echo "📝 Tipo: $project_type"
    
    case "$project_type" in
        nextjs)
            echo "🚀 URL Desarrollo: http://$SERVER_IP:3000"
            ;;
        vite)
            echo "⚡ URL Desarrollo: http://$SERVER_IP:5173"
            ;;
        django)
            echo "🎯 URL Desarrollo: http://$SERVER_IP:8000"
            ;;
        python)
            echo "🐍 URL Desarrollo: http://$SERVER_IP:5000"
            ;;
    esac
    
    echo "📊 Tamaño: $(du -sh "$project_path" | cut -f1)"
    echo ""
}

list_templates() {
    echo "🎨 Plantillas Disponibles:"
    echo ""
    echo "Frontend:"
    echo "  nextjs        - Next.js + TypeScript + Tailwind CSS"
    echo "  vite-react    - Vite + React + TypeScript"
    echo "  vite-vue      - Vite + Vue + TypeScript"
    echo ""
    echo "Backend:"
    echo "  node-express  - Node.js + Express + TypeScript"
    echo "  python-flask  - Python + Flask + CORS"
    echo "  python-django - Django + configuración básica"
    echo ""
    echo "Otros:"
    echo "  static        - HTML + CSS + JavaScript"
    echo ""
}

project_status() {
    local project_name=$1
    
    if [ -z "$project_name" ]; then
        echo "❌ Uso: $0 status [nombre-proyecto]"
        return 1
    fi
    
    local project_path="$PROJECT_DIR/$project_name"
    
    if [ ! -d "$project_path" ]; then
        echo "❌ El proyecto '$project_name' no existe"
        return 1
    fi
    
    show_project_info "$project_name"
    
    # Verificar si está corriendo
    if pgrep -f "$project_name" > /dev/null; then
        echo "🟢 Estado: CORRIENDO"
    else
        echo "🔴 Estado: DETENIDO"
    fi
}

case "$1" in
    clone)
        clone_project "$2" "$3"
        ;;
    copy)
        copy_project "$2" "$3"
        ;;
    template)
        create_from_template "$2" "$3"
        ;;
    import)
        import_project "$2" "$3"
        ;;
    list-templates)
        list_templates
        ;;
    status)
        project_status "$2"
        ;;
    *)
        show_help
        ;;
esac
