$ftpHost = "somosvela.cl"
$ftpUser = "antigravity@somosvela.cl"
$ftpPass = "!bhs18z(@j*7;3!&"

Write-Host "Limpiando la raiz de somosvela.cl..."

# Borrar index.html y architecture.html de la raiz del FTP
$filesToDelete = @("/index.html", "/architecture.html")

foreach ($file in $filesToDelete) {
    try {
        $ftpUrl = "ftp://${ftpHost}${file}"
        $request = [System.Net.FtpWebRequest]::Create($ftpUrl)
        $request.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
        $request.Method = [System.Net.WebRequestMethods+Ftp]::DeleteFile
        $response = $request.GetResponse()
        $response.Close()
        Write-Host "Eliminado de la raiz: $file"
    } catch {
        Write-Host "No se pudo eliminar de la raiz (posiblemente no existia): $file"
    }
}

Write-Host "Raiz de somosvela.cl restaurada limpiamente."
