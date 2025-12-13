[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("start","stop","restart","status","health","logs")]
  [string]$Cmd
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidDir = Join-Path $Root ".runtime"
$PidFile = Join-Path $PidDir "gateway.pid"
$LogDir = Join-Path $Root "logs"
$DateTag = (Get-Date -Format "yyyyMMdd")
$StdOutLog = Join-Path $LogDir ("gateway_{0}.out.log" -f $DateTag)
$StdErrLog = Join-Path $LogDir ("gateway_{0}.err.log" -f $DateTag)
$HostAddr = "127.0.0.1"
$Port = 10010
$HealthUrl = "http://$HostAddr`:$Port/health"

function Ensure-Dirs {
  if (!(Test-Path $PidDir)) { New-Item -ItemType Directory -Path $PidDir | Out-Null }
  if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
}

function Get-GatewayPid {
  if (!(Test-Path $PidFile)) { return $null }
  $raw = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (-not $raw) { return $null }
  try { return [int]$raw } catch { return $null }
}

function Is-GatewayRunning {
  $gwPid = Get-GatewayPid
  if (-not $gwPid) { return $false }
  try { Get-Process -Id $gwPid -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

function Wait-Health([int]$Seconds=10) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-RestMethod -Method Get -Uri $HealthUrl -TimeoutSec 2
      if ($r.ok -eq $true) { return $true }
    } catch { }
    Start-Sleep -Milliseconds 250
  }
  return $false
}

function Start-Gateway {
  Ensure-Dirs
  if (Is-GatewayRunning) { Write-Host "RUNNING"; exit 0 }

  $python = "python"
  $gw = Join-Path $Root "gateway_init_.py"
  if (!(Test-Path $gw)) { Write-Host "NOT_GREEN: gateway_init_.py missing"; exit 2 }

  $args = @("-u", $gw)

  $proc = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $Root `
          -RedirectStandardOutput $StdOutLog -RedirectStandardError $StdErrLog `
          -WindowStyle Hidden -PassThru

  Set-Content -Path $PidFile -Encoding ASCII -Value $proc.Id

  if (Wait-Health -Seconds 12) {
    Write-Host "STARTED pid=$($proc.Id)"
    exit 0
  }

  try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch { }
  Remove-Item -Force -ErrorAction SilentlyContinue $PidFile
  Write-Host "NOT_GREEN: health check failed"
  exit 3
}

function Stop-Gateway {
  if (!(Test-Path $PidFile)) { Write-Host "STOPPED"; exit 0 }

  $gwPid = Get-GatewayPid
  if (-not $gwPid) { Remove-Item -Force -ErrorAction SilentlyContinue $PidFile; Write-Host "STOPPED"; exit 0 }

  try { Stop-Process -Id $gwPid -ErrorAction Stop } catch { }

  $deadline = (Get-Date).AddSeconds(5)
  while ((Get-Date) -lt $deadline) {
    if (-not (Is-GatewayRunning)) { break }
    Start-Sleep -Milliseconds 200
  }

  try { Remove-Item -Force -ErrorAction SilentlyContinue $PidFile } catch { }

  if (Is-GatewayRunning) { Write-Host "NOT_GREEN: stop failed"; exit 4 }

  Write-Host "STOPPED"
  exit 0
}

function Status-Gateway {
  if (Is-GatewayRunning) {
    $gwPid = Get-GatewayPid
    Write-Host "RUNNING pid=$gwPid"
    exit 0
  }
  Write-Host "STOPPED"
  exit 1
}

function Health-Gateway {
  try {
    $r = Invoke-RestMethod -Method Get -Uri $HealthUrl -TimeoutSec 2
    if ($r.ok -eq $true) { Write-Host "HEALTHY"; exit 0 }
  } catch { }
  Write-Host "NOT_HEALTHY"
  exit 2
}

function Tail-Logs {
  Ensure-Dirs
  if (!(Test-Path $StdOutLog) -and !(Test-Path $StdErrLog)) { Write-Host "NO_LOGFILES"; exit 1 }

  if (Test-Path $StdOutLog) {
    Write-Host "=== STDOUT: $StdOutLog ==="
    Get-Content -Path $StdOutLog -Tail 120
  }
  if (Test-Path $StdErrLog) {
    Write-Host "=== STDERR: $StdErrLog ==="
    Get-Content -Path $StdErrLog -Tail 120
  }

  Write-Host "=== TAIL (STDOUT) ==="
  if (Test-Path $StdOutLog) { Get-Content -Path $StdOutLog -Wait -Tail 50 }
}

switch ($Cmd) {
  "start"   { Start-Gateway }
  "stop"    { Stop-Gateway }
  "restart" { & $PSCommandPath stop | Out-Null; & $PSCommandPath start }
  "status"  { Status-Gateway }
  "health"  { Health-Gateway }
  "logs"    { Tail-Logs }
}
