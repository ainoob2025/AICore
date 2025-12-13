$ErrorActionPreference = "Stop"

$Root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogDir = Join-Path $Root "logs"
$Src    = Join-Path $LogDir "gateway_requests.jsonl"
$DstDir = Join-Path $LogDir "requests"
$KeepDays = 30

New-Item -ItemType Directory -Force -Path $DstDir | Out-Null

# --- singleton lock (prevents stuck parallel runs) ---
$LockPath = Join-Path $LogDir ".rotate_gateway_logs.lock"
$lockStream = $null
try {
  $lockStream = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
  Write-Host "SKIP (already running)"
  exit 0
}

# --- ensure source exists ---
if (!(Test-Path $Src)) {
  New-Item -ItemType File -Path $Src | Out-Null
}

# --- wait until we can open exclusively (avoid file-use race) ---
$deadline = (Get-Date).AddSeconds(10)
$exclusive = $null
while ($true) {
  try {
    $exclusive = [System.IO.File]::Open($Src, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    break
  } catch {
    if ((Get-Date) -ge $deadline) {
      Write-Host "NOT_GREEN: source busy"
      exit 2
    }
    Start-Sleep -Milliseconds 200
  }
}

# --- rotate yesterday to deterministic filename ---
$tag = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
$dst = Join-Path $DstDir ("gateway_requests_{0}.jsonl" -f $tag)

try {
  $len = $exclusive.Length
  if ($len -gt 0) {
    if (Test-Path $dst) { Remove-Item -Force $dst }

    # copy current content into archive
    $exclusive.Position = 0
    $out = [System.IO.File]::Open($dst, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
    try {
      $exclusive.CopyTo($out)
      $out.Flush()
    } finally {
      $out.Dispose()
    }

    # truncate source in-place (atomic, no rename)
    $exclusive.SetLength(0)
    $exclusive.Flush()
  }
} finally {
  $exclusive.Dispose()
}

# retention
$cutoff = (Get-Date).AddDays(-$KeepDays)
Get-ChildItem -Path $DstDir -Filter "gateway_requests_*.jsonl" -File |
  Where-Object { $_.LastWriteTime -lt $cutoff } |
  Remove-Item -Force

Write-Host "ROTATED"
