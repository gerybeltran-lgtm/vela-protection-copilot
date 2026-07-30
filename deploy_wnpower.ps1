# SCRIPT DE DESPLIEGUE A SUBDIRECTORIO /vela-electric EN WNPOWER
# IMPORTANTE: NO MODIFICAR $ftpSubfolder A MENOS QUE SE QUIERA SOBREESCRIBIR EL SITIO PRINCIPAL

$ftpHost = "somosvela.cl"
$ftpUser = "antigravity@somosvela.cl"
$ftpPass = "!bhs18z(@j*7;3!&"
$ftpSubfolder = "/vela-electric"
$localDist = "G:\Mi unidad\Antigravity\Vela Electric\frontend\dist"

Write-Host "Conectando y desplegando Vela Electric en WNPower ($ftpHost$ftpSubfolder)..."

if (-not (Test-Path $localDist)) {
    Write-Host "Error: No se encontro el directorio $localDist. Ejecuta 'npm run build' dentro de frontend."
    exit 1
}

# Crear directorio base del proyecto si no existe
try {
    $makeBaseDir = [System.Net.FtpWebRequest]::Create("ftp://${ftpHost}${ftpSubfolder}")
    $makeBaseDir.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
    $makeBaseDir.Method = [System.Net.WebRequestMethods+Ftp]::MakeDirectory
    $resp = $makeBaseDir.GetResponse()
    $resp.Close()
} catch {}

Get-ChildItem -Path $localDist -Recurse | ForEach-Object {
    $relativePath = $_.FullName.Substring($localDist.Length).Replace("\", "/")
    $ftpUrl = "ftp://${ftpHost}${ftpSubfolder}${relativePath}"
    
    if ($_.PSIsContainer) {
        try {
            $makeDir = [System.Net.FtpWebRequest]::Create($ftpUrl)
            $makeDir.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
            $makeDir.Method = [System.Net.WebRequestMethods+Ftp]::MakeDirectory
            $resp = $makeDir.GetResponse()
            $resp.Close()
            Write-Host "Directorio creado/existente: $relativePath"
        } catch {
            # Ignorar si el directorio ya existe
        }
    } else {
        try {
            $webclient = New-Object System.Net.WebClient
            $webclient.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
            $webclient.UploadFile($ftpUrl, $_.FullName)
            Write-Host "Subido OK: $relativePath"
        } catch {
            Write-Host "Error al subir: $relativePath"
        }
    }
}

Write-Host "Despliegue de Vela Electric a WNPower completado en https://somosvela.cl/vela-electric !"
