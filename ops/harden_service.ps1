[CmdletBinding()]
param(
  [ValidateSet("apply","show")]
  [Parameter(Mandatory=$true)]
  [string]$Cmd
)

$ErrorActionPreference = "Stop"

$SvcName = "AICoreGateway"

function Require-Admin {
  $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) { throw "Run PowerShell as Administrator." }
}

function Apply-Hardening {
  Require-Admin

  # Least privilege: LocalService
  sc.exe config $SvcName obj= "NT AUTHORITY\LocalService" password= "" | Out-Null

  # Recovery: restart after 2s, 2s, 2s (and continue)
  # reset after 60s
  sc.exe failure $SvcName reset= 60 actions= restart/2000/restart/2000/restart/2000 | Out-Null

  # More deterministic service start behavior
  sc.exe failureflag $SvcName 1 | Out-Null

  # Start/stop timeouts (registry): ServicesPipeTimeout = 30000ms
  New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control" -Name "ServicesPipeTimeout" -PropertyType DWord -Value 30000 -Force | Out-Null

  Write-Host "APPLIED"
}

function Show-Config {
  Require-Admin
  sc.exe qc $SvcName
  sc.exe qfailure $SvcName
  Write-Host "ServicesPipeTimeout:"
  (Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control" -Name "ServicesPipeTimeout" -ErrorAction SilentlyContinue).ServicesPipeTimeout
}

switch ($Cmd) {
  "apply" { Apply-Hardening; exit 0 }
  "show"  { Show-Config; exit 0 }
}
