param(
    [int[]]$Ports = @(3000)
)

$ErrorActionPreference = "Stop"

$listeners = @()
foreach ($port in $Ports) {
    $listeners += Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
}

if (-not $listeners) {
    Write-Host ("No frontend listeners found on: " + ($Ports -join ", "))
    exit 0
}

$owners = $listeners | Select-Object -ExpandProperty OwningProcess -Unique

foreach ($owner in $owners) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $owner" -ErrorAction SilentlyContinue
    $name = if ($process) { $process.Name } else { "unknown" }
    $commandLine = if ($process -and $process.CommandLine) { $process.CommandLine } else { "" }
    Write-Host ("Stopping PID {0} ({1})" -f $owner, $name)
    if ($commandLine) {
        Write-Host ("  " + $commandLine)
    }
    Stop-Process -Id $owner -Force
}

Write-Host ("Freed ports: " + ($Ports -join ", "))
