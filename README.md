# 🚀 Servidor de Desarrollo Ubuntu

**Sistema profesional de gestión de desarrollo remoto**

[![Versión](https://img.shields.io/badge/versión-2.0-blue.svg)](https://github.com)
[![Estado](https://img.shields.io/badge/estado-activo-green.svg)](https://github.com)
[![Licencia](https://img.shields.io/badge/licencia-MIT-yellow.svg)](https://github.com)

Transforma tu PC Ubuntu en un servidor de desarrollo completo para trabajar desde cualquier dispositivo.

## ⚡ Inicio Rápido

```bash
# Ver estado del servidor
./devserver status

# Crear nuevo proyecto
./devserver new nextjs MiApp

# Iniciar desarrollo
./devserver project start MiApp
```

**📱 Accede desde tu laptop:** http://192.168.1.140:3000

## 🎯 Características Principales

- 🖥️ **Servidor SSH y Web completo**
- 🎨 **Sistema de templates profesional**
- 🚀 **Soporte para Next.js, Vite, Python**
- 🌐 **VS Code en el navegador**
- 📱 **Acceso desde Windows/Mac/Linux**
- 🔄 **Hot reload automático**
- 📦 **Gestión automática de dependencias**

## 📚 Documentación

- **[📖 Guía Completa](docs/README.md)** - Documentación detallada
- **[🪟 Guía Windows](docs/GUIA-CONEXION-WINDOWS.md)** - Conexión desde Windows
- **[🎨 Templates](templates/)** - Plantillas disponibles

## 🛠️ Comandos Esenciales

### Gestión del Servidor
```bash
./devserver status          # Estado completo
./devserver start           # Iniciar servicios
./devserver info            # Información del sistema
```

### Proyectos
```bash
./devserver projects        # Listar proyectos
./devserver new [template] [nombre]     # Nuevo proyecto
./devserver project start [nombre]     # Iniciar proyecto
./devserver clone [url] [nombre]       # Clonar desde Git
```

### Templates Disponibles
- `nextjs` - Next.js + TypeScript + Tailwind
- `vite-react` - Vite + React + TypeScript  
- `static` - HTML + CSS + JavaScript
- `node-express` - Node.js + Express API
- `python-flask` - Python + Flask API

## 🌐 Acceso Remoto

### Desde Windows
```bash
# SSH
ssh oscar@192.168.1.140

# VS Code en navegador
http://192.168.1.140:8081
```

### URLs Principales
- **Web:** http://192.168.1.140
- **Proyectos:** http://192.168.1.140/projects
- **VS Code:** http://192.168.1.140:8081

## 📁 Estructura

```
📦 reserved-ml/
├── 🎯 devserver              # Script principal
├── 📜 scripts/               # Scripts del sistema
├── 🎨 templates/             # Plantillas de proyectos
├── 📚 docs/                  # Documentación
├── ⚙️ config/                # Configuraciones
└── 🚀 [PROYECTOS]/          # Tus proyectos
```

## 🚀 Ejemplos

### Crear App Next.js
```bash
./devserver new nextjs MiEcommerce
./devserver project start MiEcommerce
# ➜ http://192.168.1.140:3000
```

### Sitio Estático
```bash
./devserver new static MiLanding
# ➜ http://192.168.1.140/projects/MiLanding
```

### Clonar Repositorio
```bash
./devserver clone https://github.com/usuario/repo.git MiProyecto
```

## 💡 Tips

- **🔄 Auto-instalación:** Las dependencias se instalan automáticamente
- **🌐 Acceso externo:** Configura port forwarding para acceso por internet  
- **💾 Persistente:** El servidor sigue funcionando aunque apagues la laptop
- **🔧 Personalizable:** Crea tus propios templates

## 🛠️ Requisitos

- Ubuntu 20.04+ 
- Node.js 18+
- Git
- SSH habilitado

## 📞 Soporte

```bash
./devserver docs     # Ver documentación completa
./devserver status   # Estado del sistema
./devserver logs     # Ver logs del sistema
```

---

**🎉 ¡Tu servidor de desarrollo está listo!**

Desarrolla desde cualquier lugar manteniendo tu Ubuntu como servidor central.

**IP del servidor:** `192.168.1.140`
