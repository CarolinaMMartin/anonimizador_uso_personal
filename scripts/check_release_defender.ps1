# Runs only on a disposable GitHub-hosted Windows machine. It never executes the portable.
param(
    [Parameter(Mandatory)][string] $Package,
    [Parameter(Mandatory)][string] $ExpectedSHA256
)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Este control de publicación requiere un runner desechable alojado por GitHub.'
}
if (-not (Get-Service WinDefend -ErrorAction SilentlyContinue)) {
    Install-WindowsFeature -Name Windows-Defender
}
if ((Get-Service WinDefend).Status -ne 'Running') { Start-Service WinDefend }
$preferences = Get-MpPreference
foreach ($type in 'ExclusionPath','ExclusionExtension','ExclusionProcess') {
    $entries = @($preferences.$type | Where-Object { $_ })
    if ($entries.Count) {
        $params = @{}
        $params[$type] = $entries
        Remove-MpPreference @params
    }
}
Set-MpPreference -DisableRealtimeMonitoring $false -DisableArchiveScanning $false
Update-MpSignature
$deadline = (Get-Date).AddSeconds(90)
do {
    $status = Get-MpComputerStatus
    if ($status.RealTimeProtectionEnabled) { break }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)
$status | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AMEngineVersion,AntivirusSignatureVersion,AntivirusSignatureLastUpdated | Format-List
if (!$status.AntivirusEnabled -or !$status.RealTimeProtectionEnabled -or $status.AntivirusSignatureAge -gt 2 -or (Get-MpPreference).DisableArchiveScanning) {
    throw 'Protección en tiempo real, firmas recientes y análisis de archivos comprimidos obligatorios.'
}
$mp = Get-ChildItem "$env:ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (!$mp) { throw 'No se encontró MpCmdRun.exe' }
function Assert-Scannable([string] $Path) {
    & $mp.FullName -CheckExclusion -Path $Path
    if ($LASTEXITCODE -ne 1) { throw "Defender no confirmó que pueda examinar $Path" }
}
function Invoke-CheckedScan([string] $Path) {
    Assert-Scannable $Path
    & $mp.FullName -Scan -ScanType 3 -File $Path
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $Path)) { throw "Falló el examen de $Path" }
}
# Some hosted images exclude their entire system and workspace drives by policy.
# Use a fresh NTFS volume whose contents can be explicitly checked for exclusions.
$letter = @('V','W','X','Y','Z' | Where-Object { !(Test-Path "${_}:\") })[0]
if (!$letter) { throw 'No hay una letra de unidad disponible.' }
$vhd = Join-Path $env:RUNNER_TEMP ("Defender-" + [guid]::NewGuid() + ".vhdx")
$diskScript = @"
create vdisk file="$vhd" maximum=3072 type=expandable
select vdisk file="$vhd"
attach vdisk
create partition primary
format fs=ntfs quick label=Revision
assign letter=$letter
"@
$commands = Join-Path $env:RUNNER_TEMP 'preparar-volumen-antivirus.txt'
$diskScript | Set-Content -LiteralPath $commands -Encoding ascii
& diskpart.exe /s $commands
if ($LASTEXITCODE -ne 0 -or !(Test-Path "${letter}:\")) { throw 'Falló la creación del volumen de examen.' }
$root = New-Item -ItemType Directory -Path "${letter}:\Revision"
Assert-Scannable $root
$zip = Join-Path $root (Split-Path -Leaf $Package)
$start = Get-Date
try {
    if ($Package -match '^https://') {
        Invoke-WebRequest -Uri $Package -OutFile $zip
    } else {
        Copy-Item -LiteralPath $Package -Destination $zip
    }
    if ((Get-FileHash $zip).Hash -ne $ExpectedSHA256) { throw 'El SHA-256 no coincide.' }
    Write-Host "SHA-256 del ZIP: $ExpectedSHA256"
    Invoke-CheckedScan $zip
    $out = Join-Path $root 'extraido'
    Expand-Archive -LiteralPath $zip -DestinationPath $out
    $exe = @(Get-ChildItem -LiteralPath $out -File -Recurse -Filter 'AnonimizadorJudicial-NLP.exe')
    if ($exe.Count -ne 1) { throw 'No se encontró el ejecutable esperado.' }
    Invoke-CheckedScan $exe[0].FullName
    Invoke-CheckedScan $out
} finally {
    $events = @(Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Windows Defender/Operational'; Id=1116,1117; StartTime=$start} -ErrorAction SilentlyContinue)
    foreach ($event in $events) { Write-Host $event.Message }
    if ($events.Count) { throw 'Defender registró una detección o remediación durante el examen.' }
}
