# Start services with better error visibility
# This version will show you exactly what's failing

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "STARTING SERVICES WITH DEBUG OUTPUT" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if port 8000 is already in use
Write-Host "[TEST] Checking if port 8000 is available..." -ForegroundColor Cyan
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "  WARNING: Port 8000 is already in use!" -ForegroundColor Yellow
    Write-Host "  Process: $($port8000.OwningProcess)" -ForegroundColor Yellow
    Write-Host "  Killing the process..." -ForegroundColor Yellow
    Stop-Process -Id $port8000.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Test 2: Check if port 5173 is already in use
Write-Host "[TEST] Checking if port 5173 is available..." -ForegroundColor Cyan
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Host "  WARNING: Port 5173 is already in use!" -ForegroundColor Yellow
    Write-Host "  Process: $($port5173.OwningProcess)" -ForegroundColor Yellow
    Write-Host "  Killing the process..." -ForegroundColor Yellow
    Stop-Process -Id $port5173.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "[TEST] Checking ngrok configuration..." -ForegroundColor Cyan

# Check for ngrok auth token
$ngrokToken = $env:NGROK_AUTH_TOKEN
if (-not $ngrokToken) {
    Write-Host '  WARNING: NGROK_AUTH_TOKEN not set in environment' -ForegroundColor Yellow
    Write-Host '  Ngrok may not work properly without authentication' -ForegroundColor Yellow
} else {
    Write-Host '  [OK] NGROK_AUTH_TOKEN is set' -ForegroundColor Green
}

# Check for ngrok domain
$ngrokDomain = $env:NGROK_DOMAIN
if ($ngrokDomain) {
    Write-Host "  [OK] NGROK_DOMAIN is set: $ngrokDomain" -ForegroundColor Green
} else {
    Write-Host '  [INFO] NGROK_DOMAIN not set (will use random ngrok domain)' -ForegroundColor Yellow
}

# Check for OAuth redirect base URL
$oauthBaseUrl = $env:OAUTH_REDIRECT_BASE_URL
if ($oauthBaseUrl) {
    Write-Host "  [OK] OAUTH_REDIRECT_BASE_URL is set: $oauthBaseUrl" -ForegroundColor Green
} else {
    Write-Host '  WARNING: OAUTH_REDIRECT_BASE_URL not set' -ForegroundColor Yellow
    Write-Host '  OAuth redirects may fail. Set this to your ngrok URL.' -ForegroundColor Yellow
}

# Check if ngrok is already running
Write-Host ""
Write-Host '[TEST] Checking for existing ngrok processes...' -ForegroundColor Cyan
$ngrokProcesses = Get-Process -Name 'ngrok' -ErrorAction SilentlyContinue
if ($ngrokProcesses) {
    Write-Host '  Found existing ngrok process(es):' -ForegroundColor Yellow
    foreach ($proc in $ngrokProcesses) {
        Write-Host "    - PID: $($proc.Id), Name: $($proc.ProcessName)" -ForegroundColor Yellow
    }
    Write-Host '  Note: Existing ngrok tunnels will be reused or replaced' -ForegroundColor Yellow
} else {
    Write-Host '  [OK] No existing ngrok processes found' -ForegroundColor Green
}

Write-Host ""
Write-Host 'Starting services...' -ForegroundColor Green
Write-Host ""
Write-Host 'Press Ctrl+C to stop all services' -ForegroundColor Yellow
Write-Host ""

# Start the main script
Write-Host ""
Write-Host 'NOTE: To start ngrok for the API server, run in a separate terminal:' -ForegroundColor Yellow
Write-Host '  .\scripts\start_ngrok_api.ps1' -ForegroundColor Cyan
Write-Host ""
Write-Host 'Or verify ngrok status with:' -ForegroundColor Yellow
Write-Host '  .\scripts\verify_ngrok.ps1' -ForegroundColor Cyan
Write-Host ""

# Start the main script
uv run python scripts/start_all.py


















