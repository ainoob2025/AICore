param(
  [string]$BaseUri = "http://127.0.0.1:10010"
)

$ErrorActionPreference = "Stop"

function Assert-Ok($cond, $msg) {
  if (-not $cond) { throw $msg }
}

function Get-Json($url) {
  Invoke-RestMethod -Method Get -Uri $url -TimeoutSec 10
}

function Post-Json($url, $obj) {
  $body = ($obj | ConvertTo-Json -Compress)
  Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $body -TimeoutSec 30
}

function Get-HttpJson-Curl($url) {
  $tmp = Join-Path $env:TEMP ("aicore_llm_" + [Guid]::NewGuid().ToString("N") + ".txt")
  $args = @("-sS", "-m", "10", "-o", $tmp, "-w", "%{http_code}", $url)
  $code = & "$env:SystemRoot\System32\curl.exe" @args
  $body = Get-Content -Path $tmp -Raw
  Remove-Item -Path $tmp -Force -ErrorAction SilentlyContinue
  return @{ StatusCode = [int]$code; Content = [string]$body }
}

Write-Host "GATE: restart service..." -ForegroundColor Cyan
.\ops\install_service.ps1 stop | Out-Null
.\ops\install_service.ps1 start | Out-Null

Write-Host "GATE: /health" -ForegroundColor Cyan
$h = Get-Json "$BaseUri/health"
Assert-Ok ($h.ok -eq $true) "/health not ok"

Write-Host "GATE: /health/llm (must respond 200 or 503 with JSON, never drop)" -ForegroundColor Cyan
$resp = Get-HttpJson-Curl "$BaseUri/health/llm"
Assert-Ok ($resp.StatusCode -eq 200 -or $resp.StatusCode -eq 503) "/health/llm unexpected HTTP status: $($resp.StatusCode)"
try { $llm = $resp.Content | ConvertFrom-Json } catch { throw "/health/llm returned non-JSON body" }
if ($resp.StatusCode -eq 200) {
  Assert-Ok ($llm.ok -eq $true) "/health/llm 200 JSON must have ok=true"
} else {
  Assert-Ok ($llm.ok -eq $false) "/health/llm 503 JSON must have ok=false"
  Assert-Ok ($llm.error -eq "LLM_UNREACHABLE") "/health/llm 503 JSON must have error=LLM_UNREACHABLE"
}

Write-Host "GATE: /metrics (required keys)" -ForegroundColor Cyan
$m = Get-Json "$BaseUri/metrics"
Assert-Ok ($m.ok -eq $true) "/metrics not ok"
$reqKeys = @(
  "requests_total","errors_total","rate_limited_total",
  "chat_inflight","max_chat_inflight","chat_busy_total",
  "plans_saved_total","last_plan_id"
)
foreach($k in $reqKeys){ Assert-Ok ($m.PSObject.Properties.Name -contains $k) "/metrics missing key: $k" }

Write-Host "GATE: /chat ping (contract + pipeline consistency)" -ForegroundColor Cyan
$r = Post-Json "$BaseUri/chat" @{ session_id="gate"; message="ping" }
Assert-Ok ($r.ok -eq $true) "/chat returned ok=false"
Assert-Ok ($null -ne $r.tool_results) "/chat missing tool_results"
Assert-Ok ($r.tool_results -is [System.Collections.IEnumerable]) "/chat tool_results is not a list/array"

$tc = 0
try { $tc = [int]$r.tool_calls_count } catch { $tc = 0 }
$tr = @($r.tool_results)

if ($tc -gt 0) {
  Assert-Ok ($tr.Count -gt 0) "/chat tool_calls_count>0 but tool_results empty"
}

# HARD FAILS: tool layer must not produce unknown tools or tool exceptions
$bad = $tr | Where-Object { $_.error -in @("UNKNOWN_TOOL","TOOL_EXCEPTION") } | Select-Object -First 1
Assert-Ok ($null -eq $bad) ("tool failure detected: " + ($bad | ConvertTo-Json -Compress))

Write-Host "GATE: checkpoint metrics moved" -ForegroundColor Cyan
$m2 = Get-Json "$BaseUri/metrics"
Assert-Ok ($m2.plans_saved_total -ge $m.plans_saved_total) "plans_saved_total did not stay monotonic"

Write-Host "GATE: kernel gate (MasterAgent invariants)" -ForegroundColor Cyan
python .\ops\kernel_gate.py

Write-Host ""
Write-Host "GATE: GREEN" -ForegroundColor Green
Write-Host ("uptime_s=" + $m2.uptime_s + " requests_total=" + $m2.requests_total + " errors_total=" + $m2.errors_total + " plans_saved_total=" + $m2.plans_saved_total)
