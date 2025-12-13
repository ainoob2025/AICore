[CmdletBinding()]
param(
  [ValidateSet("install","uninstall","start","stop","status","logs")]
  [Parameter(Mandatory=$true)]
  [string]$Cmd
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SvcName = "AICoreGateway"
$DisplayName = "AI Core Gateway"
$Description = "AI Core local gateway on 127.0.0.1:10010 (enterprise local-first)."
$WorkDir = $Root

$HostAddr = "127.0.0.1"
$Port = 10010
$HealthUrl = "http://$HostAddr`:$Port/health"

$LogDir = Join-Path $Root "logs"
$OutLog = Join-Path $LogDir "service_stdout.log"
$ErrLog = Join-Path $LogDir "service_stderr.log"

function Require-Admin {
  $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) { throw "Run PowerShell as Administrator." }
}

function Ensure-Dirs {
  if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
}

function Get-NssmPath {
  $p = Join-Path $Root "bin\nssm.exe"
  if (Test-Path $p) { return $p }
  throw "nssm.exe not found at .\bin\nssm.exe"
}

function Resolve-PythonExe {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source) { return $cmd.Source }
  throw "Python not found as 'python' on PATH."
}

function Test-PortFree {
  # True = free, False = occupied
  try {
    $c = Get-NetTCPConnection -LocalAddress $HostAddr -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($c) { return $false }
  } catch { }
  try {
    $c2 = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($c2) { return $false }
  } catch { }
  return $true
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

function Preflight-Install {
  $gw = Join-Path $Root "gateway_init_.py"
  if (!(Test-Path $gw)) { throw "gateway_init_.py missing." }

  # If something is already answering /health, we treat it as "port in use"
  try {
    $r = Invoke-RestMethod -Method Get -Uri $HealthUrl -TimeoutSec 1
    if ($r.ok -eq $true) { throw "Port $Port already serves a healthy gateway. Stop it before installing service." }
  } catch { }

  if (-not (Test-PortFree)) { throw "Port $Port is already in use. Stop the process/service using it." }
}

function Install-Service {
  Require-Admin
  Ensure-Dirs

  $nssm = Get-NssmPath
  $pyExe = Resolve-PythonExe
  $gw = Join-Path $Root "gateway_init_.py"

  Preflight-Install

  & $nssm stop $SvcName 2>$null | Out-Null
  & $nssm remove $SvcName confirm 2>$null | Out-Null

  Remove-Item -Force -ErrorAction SilentlyContinue $OutLog, $ErrLog

  & $nssm install $SvcName $pyExe | Out-Null
  & $nssm set $SvcName AppParameters "-u `"$gw`"" | Out-Null
  & $nssm set $SvcName AppDirectory $WorkDir | Out-Null

  & $nssm set $SvcName DisplayName $DisplayName | Out-Null
  & $nssm set $SvcName Description $Description | Out-Null

  & $nssm set $SvcName AppStdout $OutLog | Out-Null
  & $nssm set $SvcName AppStderr $ErrLog | Out-Null
  & $nssm set $SvcName AppStdoutCreationDisposition 2 | Out-Null  # CREATE_ALWAYS
  & $nssm set $SvcName AppStderrCreationDisposition 2 | Out-Null  # CREATE_ALWAYS

  & $nssm set $SvcName AppRotateFiles 1 | Out-Null
  & $nssm set $SvcName AppRotateOnline 1 | Out-Null
  & $nssm set $SvcName AppRotateSeconds 86400 | Out-Null
  & $nssm set $SvcName AppRotateBytes 10485760 | Out-Null

  & $nssm set $SvcName AppExit Default Restart | Out-Null
  & $nssm set $SvcName AppRestartDelay 2000 | Out-Null
  & $nssm set $SvcName Start SERVICE_AUTO_START | Out-Null

  Write-Host "INSTALLED (python=$pyExe)"
}

function Uninstall-Service {
  Require-Admin
  $nssm = Get-NssmPath
  & $nssm stop $SvcName 2>$null | Out-Null
  & $nssm remove $SvcName confirm 2>$null | Out-Null
  Write-Host "REMOVED"
}

function Start-ServiceNow {
  Require-Admin
  Start-Service -Name $SvcName
  if (Wait-Health -Seconds 10) { Write-Host "STARTED (HEALTHY)"; exit 0 }
  Write-Host "STARTED (NOT_HEALTHY)"
  exit 2
}

function Stop-ServiceNow {
  Require-Admin
  Stop-Service -Name $SvcName -Force
  Write-Host "STOPPED"
}

function Status-ServiceNow {
  try {
    $s = Get-Service -Name $SvcName -ErrorAction Stop
    Write-Host ("{0} ({1})" -f $s.Status, $SvcName)
    exit 0
  } catch {
    Write-Host "NOT_INSTALLED"
    exit 1
  }
}

function Show-Logs {
  Ensure-Dirs
  if (Test-Path $OutLog) {
    Write-Host "=== STDOUT: $OutLog ==="
    Get-Content -Path $OutLog -Tail 200
  } else { Write-Host "=== STDOUT: MISSING ===" }

  if (Test-Path $ErrLog) {
    Write-Host "=== STDERR: $ErrLog ==="
    Get-Content -Path $ErrLog -Tail 200
  } else { Write-Host "=== STDERR: MISSING ===" }
}

switch ($Cmd) {
  "install"   { Install-Service; exit 0 }
  "uninstall" { Uninstall-Service; exit 0 }
  "start"     { Start-ServiceNow }
  "stop"      { Stop-ServiceNow; exit 0 }
  "status"    { Status-ServiceNow }
  "logs"      { Show-Logs; exit 0 }
}
