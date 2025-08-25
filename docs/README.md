# 🚀 Servidor de Desarrollo Ubuntu v2.0

**Sistema profesional de desarrollo remoto para trabajar desde cualquier dispositivo**

## 📋 Tabla de Contenidos

- [🎯 Características](#-características)
- [🚀 Inicio Rápido](#-inicio-rápido)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
- [🛠️ Comandos Principales](#️-comandos-principales)
- [🎨 Sistema de Templates](#-sistema-de-templates)
- [🌐 Acceso Remoto](#-acceso-remoto)
- [🔧 Configuración Avanzada](#-configuración-avanzada)

## 🎯 Características

✅ **Servidor SSH y Web completo**  
✅ **Gestión automática de proyectos**  
✅ **Sistema de templates profesional**  
✅ **VS Code en navegador**  
✅ **Soporte para Next.js, Vite, Python**  
✅ **Hot reload automático**  
✅ **Acceso desde cualquier dispositivo**  

**IP del Servidor:** `192.168.1.140`

## 🚀 Inicio Rápido

### 1. Verificar estado del servidor
```bash
./devserver status
```

### 2. Crear tu primer proyecto
```bash
# Crear desde template
./devserver new nextjs MiEcommerce
./devserver new static MiLanding

# Clonar desde GitHub
./devserver clone https://github.com/usuario/repo.git MiProyecto
```

### 3. Iniciar desarrollo
```bash
./devserver project start MiEcommerce
# Accesible en: http://192.168.1.140:3000
```

### 4. Conectar desde Windows
```bash
# Opción 1: SSH
ssh oscar@192.168.1.140

# Opción 2: VS Code en navegador
./devserver vscode start
# Ir a: http://192.168.1.140:8081
```

## 📁 Estructura del Proyecto

```
reserved-ml/
├── devserver              # 🎯 Script principal
├── scripts/               # 📜 Scripts del sistema
│   ├── dev-server.sh      # Gestión del servidor
│   ├── project-manager.sh # Gestión de proyectos
│   ├── add-project.sh     # Alta de proyectos
│   ├── vscode-server.sh   # VS Code Server
│   └── template-manager.sh # Gestor de templates
├── templates/             # 🎨 Plantillas de proyectos
│   ├── nextjs/           # Template Next.js
│   ├── vite-react/       # Template Vite + React
│   ├── static/           # Template estático
│   └── ...
├── docs/                  # 📚 Documentación
│   ├── README.md         # Esta documentación
│   └── GUIA-WINDOWS.md   # Guía para Windows
├── config/                # ⚙️ Configuraciones
└── [PROYECTOS]/          # 🚀 Tus proyectos
```

## 🛠️ Comandos Principales

### Script Principal: `./devserver`

```bash
# ESTADO Y GESTIÓN
./devserver status          # Ver estado completo
./devserver start           # Iniciar servidor
./devserver restart         # Reiniciar servicios
./devserver info            # Información del sistema

# PROYECTOS
./devserver projects        # Listar proyectos
./devserver project start [nombre]   # Iniciar proyecto
./devserver project stop [nombre]    # Detener proyecto

# CREAR NUEVOS PROYECTOS
./devserver new nextjs MiApp        # Desde template
./devserver clone [url] [nombre]    # Desde Git
./devserver templates               # Ver templates

# HERRAMIENTAS
./devserver vscode start    # VS Code en navegador
./devserver logs           # Ver logs del sistema
./devserver update         # Actualizar sistema
```

### Gestión de Templates: `./scripts/template-manager.sh`

```bash
# TEMPLATES
./scripts/template-manager.sh list                    # Listar templates
./scripts/template-manager.sh create nextjs          # Crear template
./scripts/template-manager.sh use nextjs MiProyecto  # Usar template
./scripts/template-manager.sh edit nextjs            # Editar template
```

## 🎨 Sistema de Templates

### Templates Disponibles

| Template | Descripción | Comando |
|----------|-------------|---------|
| `nextjs` | Next.js + TypeScript + Tailwind | `./devserver new nextjs MiApp` |
| `vite-react` | Vite + React + TypeScript | `./devserver new vite-react MiApp` |
| `vite-vue` | Vite + Vue + TypeScript | `./devserver new vite-vue MiApp` |
| `node-express` | Node.js + Express API | `./devserver new node-express MiAPI` |
| `python-flask` | Python + Flask API | `./devserver new python-flask MiAPI` |
| `static` | HTML + CSS + JS | `./devserver new static MiSitio` |

### Crear Template Personalizado

1. **Crear estructura base:**
```bash
./scripts/template-manager.sh create mi-template
```

2. **Editar template:**
```bash
./scripts/template-manager.sh edit mi-template
```

3. **Usar placeholders en archivos:**
```json
{
  "name": "{{PROJECT_NAME}}",
  "description": "Proyecto {{PROJECT_NAME}}"
}
```

## 🌐 Acceso Remoto

### Desde Windows

#### Opción 1: VS Code Remote SSH
1. Instalar extensión "Remote - SSH" en VS Code
2. Conectar a: `oscar@192.168.1.140`
3. Abrir carpeta: `/home/oscar/Documentos/reserved-ml`

#### Opción 2: VS Code en Navegador
```bash
# En servidor Ubuntu:
./devserver vscode start

# En Windows, ir a:
http://192.168.1.140:8081
# Password: devserver123
```

#### Opción 3: SSH Terminal
```bash
# Desde PowerShell/CMD:
ssh oscar@192.168.1.140
```

### URLs de Acceso

- **Apache Web:** http://192.168.1.140
- **Navegador de Proyectos:** http://192.168.1.140/projects
- **VS Code:** http://192.168.1.140:8081
- **Proyecto Next.js:** http://192.168.1.140:3000
- **Proyecto Vite:** http://192.168.1.140:5173

## 🔧 Configuración Avanzada

### Variables de Entorno

Crear archivo `config/server.conf`:
```bash
SERVER_IP=192.168.1.140
PROJECT_DIR=/home/oscar/Documentos/reserved-ml
DEFAULT_NODE_VERSION=18
DEFAULT_PYTHON_VERSION=3.10
```

### Automatización con Systemd

1. **Crear servicio:**
```bash
sudo nano /etc/systemd/system/devserver.service
```

2. **Configuración:**
```ini
[Unit]
Description=Servidor de Desarrollo
After=network.target

[Service]
Type=oneshot
ExecStart=/home/oscar/Documentos/reserved-ml/devserver start
User=oscar
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

3. **Activar:**
```bash
sudo systemctl enable devserver
sudo systemctl start devserver
```

### Backup Automático

```bash
# Crear script de backup
./scripts/template-manager.sh backup

# Programar con cron
crontab -e
# Agregar: 0 2 * * * /home/oscar/Documentos/reserved-ml/scripts/backup.sh
```

### Monitoreo

```bash
# Ver logs en tiempo real
./devserver logs -f

# Monitorear recursos
./devserver info

# Ver procesos activos
./devserver project status
```

## 🚀 Ejemplos de Uso

### Desarrollo Frontend

```bash
# Crear app Next.js
./devserver new nextjs MiEcommerce
./devserver project start MiEcommerce
# ➜ http://192.168.1.140:3000

# Crear app Vite
./devserver new vite-react MiDashboard  
./devserver project start MiDashboard
# ➜ http://192.168.1.140:5173
```

### Desarrollo Backend

```bash
# API Node.js
./devserver new node-express MiAPI
./devserver project start MiAPI
# ➜ http://192.168.1.140:3000/api

# API Python
./devserver new python-flask MiAPIFlask
./devserver project start MiAPIFlask
# ➜ http://192.168.1.140:5000/api
```

### Sitio Estático

```bash
# Landing page
./devserver new static MiLanding
# ➜ http://192.168.1.140/projects/MiLanding
```

### Clonar Proyecto Existente

```bash
# Desde GitHub
./devserver clone https://github.com/vercel/next.js.git next-example
./devserver project start next-example
```

## 🔍 Solución de Problemas

### Problemas Comunes

#### SSH no conecta
```bash
sudo systemctl restart ssh
sudo ufw allow 22
```

#### Puerto ocupado
```bash
./devserver project stop all
sudo netstat -tlnp | grep :3000
```

#### VS Code no carga
```bash
./devserver vscode restart
```

#### Proyecto no inicia
```bash
cd /ruta/proyecto
npm install  # o pnpm install
./devserver project start nombre-proyecto
```

### Logs y Depuración

```bash
# Ver logs completos
./devserver logs

# Ver estado detallado
./devserver status

# Ver procesos activos
ps aux | grep -E "(next|vite|npm)"
```

## 📞 Soporte

- **Documentación completa:** `./devserver docs`
- **Estado del sistema:** `./devserver status`
- **Templates disponibles:** `./devserver templates`
- **Información del servidor:** `./devserver info`

---

**¡Tu servidor de desarrollo está listo! 🎉**

Ahora puedes desarrollar desde cualquier lugar manteniendo tu PC Ubuntu como servidor central.
