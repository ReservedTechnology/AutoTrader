# Guía de Conexión desde Laptop Windows al Servidor Ubuntu

## Información del Servidor
- **IP:** 192.168.1.140
- **Usuario:** oscar
- **Directorio de proyectos:** /home/oscar/Documentos/reserved-ml

## Métodos de Conexión

### 1. SSH (Línea de Comandos)
```bash
# Desde PowerShell o CMD en Windows
ssh oscar@192.168.1.140

# O si prefieres usar una clave SSH (recomendado)
ssh-keygen -t rsa -b 4096 -C "tu-email@ejemplo.com"
ssh-copy-id oscar@192.168.1.140
```

### 2. Visual Studio Code Remote
1. Instala la extensión "Remote - SSH" en VS Code
2. Presiona `Ctrl+Shift+P` y ejecuta "Remote-SSH: Connect to Host"
3. Ingresa: `oscar@192.168.1.140`
4. Ingresa tu contraseña
5. Abre la carpeta: `/home/oscar/Documentos/reserved-ml`

### 3. Acceso Web a Proyectos
- **Apache Web Server:** http://192.168.1.140
- **Navegador de Proyectos:** http://192.168.1.140/projects
- **API Docker:** http://192.168.1.140:8080

### 4. SFTP/FTP para transferir archivos
```bash
# Usando WinSCP, FileZilla o desde línea de comandos
sftp oscar@192.168.1.140
```

## Comandos Útiles en el Servidor

### Gestión del Servidor de Desarrollo
```bash
# Ver estado completo
./dev-server.sh status

# Reiniciar servicios
./dev-server.sh restart

# Ver proyectos disponibles
ls -la /home/oscar/Documentos/reserved-ml/
```

### Trabajar con Proyectos Next.js
```bash
# Ir al proyecto TacoManager
cd /home/oscar/Documentos/reserved-ml/TacoManager

# Instalar dependencias
npm install

# Ejecutar en modo desarrollo (accesible desde red)
npm run dev -- -H 0.0.0.0

# Luego acceder desde Windows: http://192.168.1.140:3000
```

### Trabajar con Proyectos Vite (MiCondo)
```bash
# Ir al proyecto MiCondo  
cd /home/oscar/Documentos/reserved-ml/MiCondo

# Instalar dependencias
pnpm install

# Ejecutar en modo desarrollo
pnpm dev --host 0.0.0.0

# Luego acceder desde Windows: http://192.168.1.140:5173
```

## Configuración de Firewall (si es necesario)
```bash
# En el servidor Ubuntu, permitir puertos necesarios
sudo ufw allow 22    # SSH
sudo ufw allow 80    # Apache
sudo ufw allow 3000  # Next.js dev
sudo ufw allow 5173  # Vite dev
sudo ufw allow 8080  # Docker API
```

## Mantener el Servidor Activo
El servidor seguirá funcionando incluso si apagas tu laptop. Los servicios están configurados para:
- ✅ SSH siempre activo
- ✅ Apache siempre activo  
- ✅ Docker containers persistentes
- ✅ Proyectos accesibles via web

## Trucos y Tips

### 1. Configurar VS Code para desarrollo remoto
Archivo `.vscode/settings.json` en tu proyecto:
```json
{
  "remote.SSH.remotePlatform": {
    "192.168.1.140": "linux"
  }
}
```

### 2. Sincronización automática con rsync
```bash
# Desde Windows (usando WSL o Git Bash)
rsync -av --exclude node_modules local-project/ oscar@192.168.1.140:/home/oscar/Documentos/reserved-ml/proyecto/
```

### 3. Ejecutar comandos remotos sin conectarse
```bash
# Desde Windows
ssh oscar@192.168.1.140 "cd /home/oscar/Documentos/reserved-ml/TacoManager && npm run build"
```

### 4. Tunnel SSH para desarrollo local
```bash
# Hacer que el puerto 3000 del servidor esté disponible localmente en Windows
ssh -L 3000:localhost:3000 oscar@192.168.1.140
```

## Solución de Problemas

### Si no puedes conectar por SSH:
```bash
# En el servidor Ubuntu
sudo systemctl status ssh
sudo systemctl restart ssh
```

### Si los puertos no están disponibles:
```bash
# Verificar qué está usando los puertos
sudo netstat -tlnp | grep :3000
```

### Si Apache no sirve los archivos:
```bash
# Verificar permisos
sudo chown -R oscar:www-data /home/oscar/Documentos/reserved-ml
sudo chmod -R 755 /home/oscar/Documentos/reserved-ml
```
