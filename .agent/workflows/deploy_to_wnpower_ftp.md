# Guía de Despliegue Automático a WNPower (Vela Electric)

Esta guía enseña a cualquier agente AI cómo desplegar la aplicación **Vela Electric** en el hosting de **WNPower** vía FTP.

## Credenciales y Configuración WNPower

- **Servidor FTP**: `somosvela.cl`
- **Usuario FTP**: `antigravity@somosvela.cl`
- **Contraseña FTP**: `!bhs18z(@j*7;3!&`
- **Carpeta de Despliegue Frontend**: `G:\Mi unidad\Antigravity\Vela Electric\frontend\dist`

---

## Flujo de Trabajo para el Agente AI

### 1. Compilación
```powershell
cd "g:\Mi unidad\Antigravity\Vela Electric\frontend"
npm run build
```

### 2. Despliegue por FTP
```powershell
powershell -ExecutionPolicy Bypass -File "g:\Mi unidad\Antigravity\Vela Electric\deploy_wnpower.ps1"
```

El script utiliza clases `.NET System.Net.WebClient` integradas en Windows para subir automáticamente todos los estáticos directos al cPanel de WNPower.
