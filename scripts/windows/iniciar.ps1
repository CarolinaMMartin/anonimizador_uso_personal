param([switch]$Verify, [switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$packageDir = [IO.Path]::GetFullPath($PSScriptRoot)
$frontendDir = Join-Path $packageDir 'frontend'
$portFile = Join-Path $packageDir 'PUERTO_ACTUAL.txt'
$versionFile = Join-Path $packageDir 'VERSION_APP.txt'
$exePath = Join-Path $packageDir 'AnonimizadorJudicial-NLP.exe'

function Get-PackageHealth([int]$Port) {
    try {
        $request = [Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/health")
        $request.Proxy = $null
        $request.AllowAutoRedirect = $false
        $request.Timeout = 1500
        $request.ReadWriteTimeout = 1500
        $response = $request.GetResponse()
        try {
            $reader = [IO.StreamReader]::new($response.GetResponseStream())
            try { $health = $reader.ReadToEnd() | ConvertFrom-Json }
            finally { $reader.Dispose() }
        } finally { $response.Dispose() }
        $servedFrontend = [IO.Path]::GetFullPath([string]$health.frontend_dir)
        if ($health.status -eq 'ok' -and $health.app_version -eq $version -and
            [int]$health.port -eq $Port -and
            [string]::Equals($servedFrontend, $frontendDir, [StringComparison]::OrdinalIgnoreCase)) {
            return $health
        }
    } catch { }
    return $null
}

function Test-FreePort([int]$Port) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Server.ExclusiveAddressUse = $true
        $listener.Start()
        return $true
    } catch { return $false }
    finally { $listener.Stop() }
}

function Show-Application([int]$Port) {
    $url = "http://127.0.0.1:$Port"
    if ($Verify) { $url += '/health' }
    Write-Host "Anonimizador Judicial $version - $url"
    if (-not $NoBrowser) { Start-Process -FilePath $url }
}

$mutex = $null
$locked = $false
try {
    if (-not (Test-Path -LiteralPath $versionFile -PathType Leaf)) {
        throw 'Falta VERSION_APP.txt. Extrae nuevamente la carpeta completa de esta version.'
    }
    $version = (Get-Content -LiteralPath $versionFile -Raw).Trim()
    if (-not $version) { throw 'VERSION_APP.txt esta vacio.' }

    # Serialize double clicks for this package, including while it starts.
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $key = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($packageDir.ToLowerInvariant()))).Replace('-', '') }
    finally { $sha.Dispose() }
    $mutex = [Threading.Mutex]::new($false, "Local\Anonimizador-$key")
    try { $locked = $mutex.WaitOne(65000) }
    catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Esta version todavia esta iniciando. Espera unos segundos y vuelve a abrirla.' }

    $ports = @(8787..8796)
    if (Test-Path -LiteralPath $portFile -PathType Leaf) {
        [int]$savedPort = 0
        if ([int]::TryParse((Get-Content -LiteralPath $portFile -Raw).Trim(), [ref]$savedPort) -and
            $savedPort -ge 8787 -and $savedPort -le 8796) {
            $ports = @($savedPort) + @($ports | Where-Object { $_ -ne $savedPort })
        }
    }
    $freePort = $null
    foreach ($candidate in $ports) {
        if (Test-FreePort $candidate) {
            if ($null -eq $freePort) { $freePort = $candidate }
        } elseif ($null -ne (Get-PackageHealth $candidate)) {
            Write-Host 'Esta version ya esta abierta. Se conserva la instancia existente.'
            Set-Content -LiteralPath $portFile -Value $candidate -Encoding ASCII
            Show-Application $candidate
            exit 0
        }
    }
    if ($Verify) { throw 'Esta version no esta abierta. Ejecuta INICIAR.bat primero.' }
    if ($null -eq $freePort) { throw 'No hay un puerto libre entre 8787 y 8796. Las aplicaciones abiertas se conservaron.' }
    if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) { throw 'Falta el ejecutable. Extrae la carpeta completa.' }

    Write-Host "Iniciando la version $version en el puerto $freePort..."
    if ($freePort -ne 8787) { Write-Host 'El puerto 8787 esta ocupado; la otra copia permanecera abierta.' }
    $previousPort = $env:ANON_PORT
    $previousFrontend = $env:ANON_FRONTEND_DIR
    $previousBrowser = $env:ANON_NO_BROWSER
    try {
        $env:ANON_PORT = [string]$freePort
        $env:ANON_FRONTEND_DIR = $frontendDir
        if ($NoBrowser) { $env:ANON_NO_BROWSER = '1' }
        $process = Start-Process -FilePath $exePath -WorkingDirectory $packageDir -WindowStyle Hidden -PassThru
    } finally {
        $env:ANON_PORT = $previousPort
        $env:ANON_FRONTEND_DIR = $previousFrontend
        $env:ANON_NO_BROWSER = $previousBrowser
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        if ($null -ne (Get-PackageHealth $freePort)) {
            Set-Content -LiteralPath $portFile -Value $freePort -Encoding ASCII
            # The executable opens its browser on startup.
            Write-Host "Version $version lista: http://127.0.0.1:$freePort"
            exit 0
        }
        if ($process.HasExited) { throw 'La aplicacion termino antes de iniciar. Revisa que la carpeta este completa.' }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "El inicio tarda mas de lo esperado. Revisa http://127.0.0.1:$freePort antes de volver a ejecutar INICIAR.bat."
} catch {
    Write-Host "No se pudo abrir esta version: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    if ($null -ne $mutex) { $mutex.Dispose() }
}
