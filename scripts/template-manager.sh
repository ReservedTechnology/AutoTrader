#!/bin/bash

# =============================================================================
# 🎨 GESTOR DE TEMPLATES - SERVIDOR DE DESARROLLO
# =============================================================================
# Gestión avanzada de plantillas para nuevos proyectos
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(dirname "$SCRIPT_DIR")/templates"
PROJECT_DIR="/home/oscar/Documentos/reserved-ml"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Registro de templates disponibles
declare -A TEMPLATES
TEMPLATES[nextjs]="Next.js + TypeScript + Tailwind CSS"
TEMPLATES[vite-react]="Vite + React + TypeScript"
TEMPLATES[vite-vue]="Vite + Vue + TypeScript"  
TEMPLATES[node-express]="Node.js + Express + TypeScript"
TEMPLATES[python-flask]="Python + Flask + CORS"
TEMPLATES[python-django]="Django + PostgreSQL ready"
TEMPLATES[static]="HTML + CSS + JavaScript"

list_templates() {
    echo "🎨 TEMPLATES DISPONIBLES:"
    echo ""
    
    echo "📱 FRONTEND:"
    [ -d "$TEMPLATES_DIR/nextjs" ] && echo "  ✅ nextjs        - ${TEMPLATES[nextjs]}" || echo "  📦 nextjs        - ${TEMPLATES[nextjs]} (crear)"
    [ -d "$TEMPLATES_DIR/vite-react" ] && echo "  ✅ vite-react    - ${TEMPLATES[vite-react]}" || echo "  📦 vite-react    - ${TEMPLATES[vite-react]} (crear)"
    [ -d "$TEMPLATES_DIR/vite-vue" ] && echo "  ✅ vite-vue      - ${TEMPLATES[vite-vue]}" || echo "  📦 vite-vue      - ${TEMPLATES[vite-vue]} (crear)"
    
    echo ""
    echo "🔧 BACKEND:"
    [ -d "$TEMPLATES_DIR/node-express" ] && echo "  ✅ node-express  - ${TEMPLATES[node-express]}" || echo "  📦 node-express  - ${TEMPLATES[node-express]} (crear)"
    [ -d "$TEMPLATES_DIR/python-flask" ] && echo "  ✅ python-flask  - ${TEMPLATES[python-flask]}" || echo "  📦 python-flask  - ${TEMPLATES[python-flask]} (crear)"
    [ -d "$TEMPLATES_DIR/python-django" ] && echo "  ✅ python-django - ${TEMPLATES[python-django]}" || echo "  📦 python-django - ${TEMPLATES[python-django]} (crear)"
    
    echo ""
    echo "🌐 OTROS:"
    [ -d "$TEMPLATES_DIR/static" ] && echo "  ✅ static        - ${TEMPLATES[static]}" || echo "  📦 static        - ${TEMPLATES[static]} (crear)"
    
    echo ""
    echo "COMANDOS:"
    echo "  $0 create [template]     - Crear/actualizar template"
    echo "  $0 use [template] [name] - Usar template para proyecto"
    echo "  $0 edit [template]       - Editar template existente"
    echo "  $0 backup               - Hacer backup de templates"
}

create_template() {
    local template_name=$1
    
    if [ -z "$template_name" ]; then
        log_error "Especifica el template: $0 create [template]"
        return 1
    fi
    
    if [[ ! ${TEMPLATES[$template_name]+_} ]]; then
        log_error "Template '$template_name' no reconocido"
        list_templates
        return 1
    fi
    
    local template_dir="$TEMPLATES_DIR/$template_name"
    
    log_info "Creando template: $template_name"
    mkdir -p "$template_dir"
    
    case "$template_name" in
        nextjs)
            create_nextjs_template "$template_dir"
            ;;
        vite-react)
            create_vite_react_template "$template_dir"
            ;;
        vite-vue)
            create_vite_vue_template "$template_dir"
            ;;
        node-express)
            create_node_express_template "$template_dir"
            ;;
        python-flask)
            create_python_flask_template "$template_dir"
            ;;
        python-django)
            create_python_django_template "$template_dir"
            ;;
        static)
            create_static_template "$template_dir"
            ;;
    esac
    
    log_success "Template '$template_name' creado en: $template_dir"
}

create_nextjs_template() {
    local template_dir=$1
    
    # package.json
    cat > "$template_dir/package.json" << 'EOF'
{
  "name": "{{PROJECT_NAME}}",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -H 0.0.0.0",
    "build": "next build",
    "start": "next start -H 0.0.0.0",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.2.31",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/node": "^24.2.0",
    "@types/react": "^19.1.9",
    "@types/react-dom": "^19.1.7",
    "autoprefixer": "^10.4.21",
    "eslint": "^9.33.0",
    "eslint-config-next": "^15.4.6",
    "postcss": "^8.5.6",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.9.2"
  }
}
EOF

    # next.config.js
    cat > "$template_dir/next.config.js" << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
}

module.exports = nextConfig
EOF

    # tsconfig.json
    cat > "$template_dir/tsconfig.json" << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
EOF

    # Estructura de directorios y archivos
    mkdir -p "$template_dir/src/app"
    mkdir -p "$template_dir/public"
    
    # layout.tsx
    cat > "$template_dir/src/app/layout.tsx" << 'EOF'
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '{{PROJECT_NAME}}',
  description: 'Aplicación Next.js',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  )
}
EOF

    # page.tsx
    cat > "$template_dir/src/app/page.tsx" << 'EOF'
export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {{PROJECT_NAME}}
        </h1>
        <p className="text-xl text-gray-600">
          Proyecto Next.js listo para desarrollar
        </p>
      </div>
    </main>
  )
}
EOF

    # globals.css
    cat > "$template_dir/src/app/globals.css" << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: system-ui, -apple-system, sans-serif;
}
EOF

    # tailwind.config.js
    cat > "$template_dir/tailwind.config.js" << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

    # README.md
    cat > "$template_dir/README.md" << 'EOF'
# {{PROJECT_NAME}}

Proyecto Next.js creado con el servidor de desarrollo.

## Desarrollo

```bash
npm run dev
```

## Construcción

```bash
npm run build
npm start
```
EOF

    log_success "Template Next.js creado"
}

create_static_template() {
    local template_dir=$1
    
    mkdir -p "$template_dir/css" "$template_dir/js" "$template_dir/images"
    
    # index.html
    cat > "$template_dir/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{PROJECT_NAME}}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>{{PROJECT_NAME}}</h1>
    </header>
    <main>
        <section class="hero">
            <h2>¡Bienvenido!</h2>
            <p>Tu proyecto estático está listo.</p>
            <button onclick="saludar()">Saludar</button>
        </section>
    </main>
    <footer>
        <p>&copy; 2025 {{PROJECT_NAME}}</p>
    </footer>
    <script src="js/main.js"></script>
</body>
</html>
EOF

    # CSS
    cat > "$template_dir/css/style.css" << 'EOF'
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

header {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    padding: 1rem;
    text-align: center;
    color: white;
}

header h1 {
    font-size: 2.5rem;
    font-weight: 300;
}

main {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: calc(100vh - 200px);
    padding: 2rem;
}

.hero {
    background: rgba(255, 255, 255, 0.95);
    padding: 3rem;
    border-radius: 20px;
    text-align: center;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
    max-width: 500px;
}

.hero h2 {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #333;
}

.hero p {
    font-size: 1.1rem;
    margin-bottom: 2rem;
    color: #666;
}

button {
    background: linear-gradient(45deg, #667eea, #764ba2);
    color: white;
    border: none;
    padding: 12px 24px;
    font-size: 1rem;
    border-radius: 25px;
    cursor: pointer;
    transition: transform 0.2s;
}

button:hover {
    transform: translateY(-2px);
}

footer {
    text-align: center;
    padding: 1rem;
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.9rem;
}
EOF

    # JavaScript
    cat > "$template_dir/js/main.js" << 'EOF'
// {{PROJECT_NAME}} - JavaScript principal

console.log('{{PROJECT_NAME}} cargado correctamente');

function saludar() {
    alert('¡Hola desde {{PROJECT_NAME}}!');
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado - Proyecto listo');
    
    // Agregar animación suave al botón
    const button = document.querySelector('button');
    if (button) {
        button.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
        });
    }
});

// Funciones útiles para el proyecto
const utils = {
    // Función para hacer requests
    async fetchData(url) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    },
    
    // Función para formatear fechas
    formatDate(date) {
        return new Date(date).toLocaleDateString('es-ES');
    }
};

window.utils = utils;
EOF

    # README.md
    cat > "$template_dir/README.md" << 'EOF'
# {{PROJECT_NAME}}

Proyecto web estático creado con el servidor de desarrollo.

## Estructura

- `index.html` - Página principal
- `css/style.css` - Estilos
- `js/main.js` - JavaScript
- `images/` - Imágenes

## Desarrollo

Simplemente abre `index.html` en tu navegador o accede via:
http://192.168.1.140/projects/{{PROJECT_NAME}}
EOF

    log_success "Template estático creado"
}

use_template() {
    local template_name=$1
    local project_name=$2
    
    if [ -z "$template_name" ] || [ -z "$project_name" ]; then
        log_error "Uso: $0 use [template] [nombre]"
        return 1
    fi
    
    local template_dir="$TEMPLATES_DIR/$template_name"
    local project_dir="$PROJECT_DIR/$project_name"
    
    if [ ! -d "$template_dir" ]; then
        log_error "Template '$template_name' no existe"
        log_info "Créalo primero con: $0 create $template_name"
        return 1
    fi
    
    if [ -d "$project_dir" ]; then
        log_error "El proyecto '$project_name' ya existe"
        return 1
    fi
    
    log_info "Creando proyecto '$project_name' desde template '$template_name'"
    
    # Copiar template
    cp -r "$template_dir" "$project_dir"
    
    # Reemplazar placeholders
    find "$project_dir" -type f -name "*.json" -o -name "*.html" -o -name "*.md" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.css" | \
    xargs sed -i "s/{{PROJECT_NAME}}/$project_name/g"
    
    # Establecer permisos
    chown -R oscar:www-data "$project_dir" 2>/dev/null || true
    chmod -R 755 "$project_dir" 2>/dev/null || true
    
    log_success "Proyecto '$project_name' creado exitosamente"
    echo "📁 Ubicación: $project_dir"
    echo "🌐 URL: http://192.168.1.140/projects/$project_name"
    
    # Instalar dependencias si es necesario
    if [ -f "$project_dir/package.json" ]; then
        log_info "Instalando dependencias..."
        cd "$project_dir"
        npm install
    fi
}

edit_template() {
    local template_name=$1
    
    if [ -z "$template_name" ]; then
        log_error "Especifica el template: $0 edit [template]"
        return 1
    fi
    
    local template_dir="$TEMPLATES_DIR/$template_name"
    
    if [ ! -d "$template_dir" ]; then
        log_error "Template '$template_name' no existe"
        return 1
    fi
    
    echo "📁 Editando template: $template_dir"
    echo "Archivos disponibles:"
    find "$template_dir" -type f | head -10
    
    if command -v code >/dev/null; then
        code "$template_dir"
    else
        echo "Para editar, ve a: $template_dir"
    fi
}

backup_templates() {
    local backup_dir="$PROJECT_DIR/backups/templates-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    if [ -d "$TEMPLATES_DIR" ]; then
        cp -r "$TEMPLATES_DIR" "$backup_dir/"
        log_success "Backup creado en: $backup_dir"
    else
        log_warning "No hay templates para respaldar"
    fi
}

case "$1" in
    list|ls)
        list_templates
        ;;
    create)
        create_template "$2"
        ;;
    use)
        use_template "$2" "$3"
        ;;
    edit)
        edit_template "$2"
        ;;
    backup)
        backup_templates
        ;;
    *)
        echo "🎨 Gestor de Templates"
        echo ""
        echo "Uso: $0 [comando] [opciones]"
        echo ""
        echo "Comandos:"
        echo "  list                    - Listar templates disponibles"
        echo "  create [template]       - Crear/actualizar template"
        echo "  use [template] [nombre] - Usar template para nuevo proyecto"
        echo "  edit [template]         - Editar template existente"
        echo "  backup                  - Hacer backup de templates"
        echo ""
        list_templates
        ;;
esac
