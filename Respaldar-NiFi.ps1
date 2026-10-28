# Ejecutar desde PowerShell DESPUES de detener NiFi ordenadamente.
# No detiene, elimina ni recrea contenedores. No altera los volumenes fuente.
$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $raiz 'docker-compose.yml'))) {
    throw 'Coloca este script junto al docker-compose.yml vigente.'
}
$infoTexto = & docker inspect nifi_tesis
if ($LASTEXITCODE -ne 0) { throw 'No se pudo inspeccionar nifi_tesis.' }
$info = @($infoTexto | ConvertFrom-Json)[0]
if ($info.State.Running) { throw 'NiFi sigue funcionando. Deten sus componentes y luego el contenedor antes del respaldo.' }
if ($info.State.ExitCode -eq 137 -or $info.State.OOMKilled) {
    throw 'NiFi no termino limpiamente (137/OOM). No usar este respaldo como punto consistente; revisar antes de reemplazar.'
}
if ($info.Config.Labels.'com.docker.compose.project' -ne 'prototipotesis') {
    throw 'El proyecto Compose no coincide con el inventario revisado.'
}
$esperados = @{
    content_repository = '811bd8646a5b3e8820af4e5794f4ef6a76f701f723c95134f779f973f2ac5a6f'
    flowfile_repository = '2c1185f62bd98c08965caa0f852962a5c0a244a0b1db772d0dfb933d036ae56b'
    database_repository = '61cfd30754d613531cbea1e92bac1ca23d697b9494638433ff1cb513677f09b0'
    provenance_repository = 'e3ce6b024e002a401570263647b0d86ea7983f38b7e3937100dcfc2e261a35d3'
    state = '2c81b9572290c20740f9acb19a47cd5a4c5edc5ef57b70f081b80e21c7fb6919'
    logs = '2176f91c4387b130d2b14185661685ea302bf7fb2bbc732e9d61882fa0d41e34'
    python_extensions = '2055bf61092ce9a2aaa1afd31c7a54b238b2721c7ca471915bc002cc23ed6073'
    nar_extensions = 'ae46f7d91b3ddcc586d7e64cd3ff21562be81b6c9dd26c9b1ed8a03d68694a79'
}
foreach ($nombre in $esperados.Keys) {
    $ruta = '/opt/nifi/nifi-current/' + $nombre
    $montaje = @($info.Mounts | Where-Object { $_.Destination -eq $ruta })
    if ($montaje.Count -ne 1 -or $montaje[0].Name -ne $esperados[$nombre]) {
        throw "Montaje distinto del inventario para $nombre. Detener aqui y revisar."
    }
}
$confEsperada = [IO.Path]::GetFullPath((Join-Path $raiz 'nifi-conf')).TrimEnd('\')
$confMontaje = @($info.Mounts | Where-Object { $_.Destination -eq '/opt/nifi/nifi-current/conf' })
if ($confMontaje.Count -ne 1 -or $confMontaje[0].Type -ne 'bind' -or $confMontaje[0].Source.TrimEnd('\') -ine $confEsperada) {
    throw 'La carpeta de configuracion no coincide con la ubicacion de este script.'
}
$respaldo = Join-Path $raiz ('respaldos\nifi-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $respaldo | Out-Null
$carpetas = @('conf', 'content_repository', 'flowfile_repository', 'database_repository', 'provenance_repository', 'state', 'logs', 'python_extensions', 'nar_extensions')
foreach ($carpeta in $carpetas) {
    Write-Host "Copiando $carpeta ..."
    $origen = 'nifi_tesis:/opt/nifi/nifi-current/' + $carpeta
    $destino = Join-Path $respaldo $carpeta
    & docker cp $origen $destino
    if ($LASTEXITCODE -ne 0) { throw "Fallo copiando $carpeta. Respaldo incompleto; no recrear NiFi." }
}
& docker cp 'nifi_tesis:/opt/scripts' (Join-Path $respaldo 'scripts')
if ($LASTEXITCODE -ne 0) { throw 'Fallo copiando scripts. Respaldo incompleto.' }
Copy-Item -LiteralPath (Join-Path $raiz 'docker-compose.yml') -Destination (Join-Path $respaldo 'docker-compose.anterior.yml')
if (Test-Path -LiteralPath (Join-Path $raiz '.env')) {
    Copy-Item -LiteralPath (Join-Path $raiz '.env') -Destination (Join-Path $respaldo '.env')
}
$info.Mounts | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $respaldo 'montajes.json') -Encoding UTF8
@{
    image_id = $info.Image
    container_id = $info.Id
    fecha_respaldo = (Get-Date).ToString('o')
    proyecto = $info.Config.Labels.'com.docker.compose.project'
    estado = 'COPIA_COMPLETADA'
    alcance = 'Configuracion y repositorios NiFi; scripts y Compose. No incluye data, MySQL ni AWS.'
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $respaldo 'resumen.json') -Encoding UTF8
'Copia completada. No equivale a una restauracion ensayada.' | Set-Content -LiteralPath (Join-Path $respaldo 'RESPALDO_COMPLETADO.txt') -Encoding UTF8
Write-Host "RESPALDO_COMPLETADO: $respaldo"
Write-Host 'Conserva esta carpeta de forma privada: contiene configuracion y credenciales.'
