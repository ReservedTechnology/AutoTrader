# Servidor de Desarrollo Ubuntu

Tu PC de escritorio Ubuntu está configurado como un servidor de desarrollo completo para trabajar desde cualquier lugar, especialmente desde tu laptop Windows.

## 🎯 Estado Actual

✅ **SSH Server** - Puerto 22  
✅ **Apache Web Server** - Puerto 80  
✅ **Docker Containers** - Puerto 8080  
✅ **Proyectos accesibles via web**  

**IP del Servidor:** `192.168.1.140`

## 🚀 Scripts Disponibles

### 1. `./dev-server.sh` - Gestión General del Servidor
```bash
./dev-server.sh start    # Iniciar todos los servicios
./dev-server.sh status   # Ver estado completo
./dev-server.sh restart  # Reiniciar servicios
```

### 2. `./project-manager.sh` - Gestión de Proyectos
```bash
./project-manager.sh list               # Listar proyectos
./project-manager.sh start TacoManager  # Iniciar proyecto específico
./project-manager.sh stop TacoManager   # Detener proyecto
./project-manager.sh ps                 # Ver procesos activos
```

### 3. `./add-project.sh` - Dar de Alta Nuevos Proyectos
```bash
./add-project.sh clone [url] [nombre]     # Clonar desde Git
./add-project.sh template nextjs MiApp   # Crear desde plantilla
./add-project.sh copy [origen] [nombre]  # Copiar proyecto local
./add-project.sh list-templates          # Ver plantillas disponibles
```

### 4. `./vscode-server.sh` - VS Code en el Navegador
```bash
./vscode-server.sh install  # Instalar VS Code Server
./vscode-server.sh start    # Iniciar VS Code en navegador
./vscode-server.sh status   # Ver estado
```

## 🌐 Acceso desde Windows

### Método 1: SSH + VS Code Remote
```bash
# Desde PowerShell en Windows
ssh oscar@192.168.1.140
```

En VS Code Windows:
1. Instalar extensión "Remote - SSH"
2. Conectar a `oscar@192.168.1.140`
3. Abrir carpeta `/home/oscar/Documentos/reserved-ml`

### Método 2: VS Code en Navegador
1. Ejecutar en servidor: `./vscode-server.sh start`
2. Abrir en Windows: http://192.168.1.140:8081
3. Password: `devserver123`

### Método 3: Navegador Web Simple
- **Proyectos:** http://192.168.1.140/projects
- **Apache:** http://192.168.1.140
- **Docker API:** http://192.168.1.140:8080

## 📁 Proyectos Disponibles

| Proyecto | Tipo | URL Desarrollo |
|----------|------|----------------|
| TacoManager | Next.js | http://192.168.1.140:3000 |
| MiCondo | Vite | http://192.168.1.140:5173 |
| AuditaConstruccion | General | http://192.168.1.140/projects/AuditaConstruccion |
| AutenticaTequilera | General | http://192.168.1.140/projects/AutenticaTequilera |
| Importala | General | http://192.168.1.140/projects/Importala |
| ReservedCalendarPro | General | http://192.168.1.140/projects/ReservedCalendarPro |
| TrasladaAuto | General | http://192.168.1.140/projects/TrasladaAuto |

## ⚡ Inicio Rápido

### Para Crear un Nuevo Proyecto:
```bash
# Crear desde plantilla
./add-project.sh template nextjs MiNuevoEcommerce
./add-project.sh template vite-react MiAppReact  
./add-project.sh template python-flask MiAPIFlask

# Clonar desde GitHub
./add-project.sh clone https://github.com/usuario/repo.git MiProyectoClonado

# Ver plantillas disponibles
./add-project.sh list-templates
```

### Para Trabajar en TacoManager (Next.js):
```bash
./project-manager.sh start TacoManager
# Luego abrir en Windows: http://192.168.1.140:3000
```

### Para Trabajar en MiCondo (Vite):
```bash  
./project-manager.sh start MiCondo
# Luego abrir en Windows: http://192.168.1.140:5173
```

### Para Usar VS Code Completo:
```bash
./vscode-server.sh install  # Solo la primera vez
./vscode-server.sh start
# Luego abrir en Windows: http://192.168.1.140:8081
```

## 🔧 Configuración Avanzada

### Agregar Nuevo Proyecto
1. Clonar/copiar proyecto a `/home/oscar/Documentos/reserved-ml/`
2. Ejecutar `./project-manager.sh list` para verificar
3. Usar `./project-manager.sh start [nombre-proyecto]`

### Configurar Puerto Personalizado
Editar el script del proyecto específico o usar:
```bash
# Para Next.js en puerto personalizado
cd TacoManager && npm run dev -- -H 0.0.0.0 -p 3001

# Para Vite en puerto personalizado  
cd MiCondo && pnpm dev --host 0.0.0.0 --port 5174
```

### Acceso Externo (Internet)
Si quieres acceso desde internet (no solo red local):
```bash
# Configurar router/modem para port forwarding:
# Puerto 22 (SSH) -> 192.168.1.140:22
# Puerto 80 (Web) -> 192.168.1.140:80
# Puerto 8081 (VS Code) -> 192.168.1.140:8081
```

## 🛠️ Mantenimiento

### Logs y Monitoreo
```bash
# Ver logs del sistema
sudo journalctl -f

# Ver uso de recursos
htop

# Ver conexiones de red
sudo netstat -tulpn

# Espacio en disco
df -h
```

### Backup Automático
```bash
# Crear script de backup (ejemplo)
rsync -av /home/oscar/Documentos/reserved-ml/ /backup/projects/
```

### Actualizaciones
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade

# Actualizar Node.js projects
cd TacoManager && npm update
cd ../MiCondo && pnpm update
```

## 📞 Solución de Problemas

### Si no puedes conectarte por SSH:
```bash
sudo systemctl restart ssh
sudo ufw allow 22
```

### Si los proyectos no cargan:
```bash
./project-manager.sh ps  # Ver procesos activos
./project-manager.sh stop all  # Detener todo
./project-manager.sh start [proyecto]  # Reiniciar proyecto específico
```

### Si VS Code Server no funciona:
```bash
./vscode-server.sh stop
./vscode-server.sh start
```

### Si Apache no sirve archivos:
```bash
sudo systemctl restart apache2
sudo chown -R oscar:www-data /home/oscar/Documentos/reserved-ml
```

## 🎉 ¡Listo!

Tu servidor de desarrollo está completamente configurado. Ahora puedes:

1. **Trabajar desde tu laptop Windows** como si fuera local
2. **Mantener el servidor corriendo** 24/7 
3. **Acceder a todos tus proyectos** desde cualquier dispositivo en la red
4. **Usar VS Code completo** en el navegador
5. **Desarrollar en tiempo real** con hot-reload

**¡Disfruta programando desde cualquier lugar! 🚀**
