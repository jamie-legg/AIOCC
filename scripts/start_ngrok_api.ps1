# Start ngrok tunnel for API server on port 8000
# This ensures the API is accessible via public URL for OAuth

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  STARTING NGROK FOR API SERVER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if API is running
Write-Host "[CHECK] Verifying API server is running..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ API server is running on port 8000" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ API server is NOT running on port 8000" -ForegroundColor Red
    Write-Host "  Please start the API server first!" -ForegroundColor Yellow
    exit 1
}

# Check for ngrok token
$ngrokToken = $env:NGROK_AUTH_TOKEN
if (-not $ngrokToken) {
    Write-Host ""
    Write-Host "[WARNING] NGROK_AUTH_TOKEN not set" -ForegroundColor Yellow
    Write-Host "  Ngrok will work but with limitations" -ForegroundColor Yellow
    Write-Host "  Get a free token at: https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor Yellow
}

# Check for reserved domain
$ngrokDomain = $env:NGROK_DOMAIN
if ($ngrokDomain) {
    Write-Host ""
    Write-Host "[INFO] Using reserved domain: $ngrokDomain" -ForegroundColor Cyan
    $domainArg = "--domain=$ngrokDomain"
} else {
    Write-Host ""
    Write-Host "[INFO] Using random ngrok domain" -ForegroundColor Cyan
    $domainArg = ""
}

# Check if ngrok is already running
Write-Host ""
Write-Host "[CHECK] Checking for existing ngrok processes..." -ForegroundColor Cyan
$ngrokProcesses = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($ngrokProcesses) {
    Write-Host "  Found existing ngrok process(es)" -ForegroundColor Yellow
    Write-Host "  Stopping existing ngrok processes..." -ForegroundColor Yellow
    foreach ($proc in $ngrokProcesses) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Start ngrok
Write-Host ""
Write-Host "[START] Starting ngrok tunnel..." -ForegroundColor Cyan
if ($domainArg) {
    Write-Host "  Command: ngrok http 8000 $domainArg" -ForegroundColor White
    Start-Process -FilePath "ngrok" -ArgumentList "http", "8000", $domainArg -NoNewWindow
} else {
    Write-Host "  Command: ngrok http 8000" -ForegroundColor White
    Start-Process -FilePath "ngrok" -ArgumentList "http", "8000" -NoNewWindow
}

# Wait for ngrok to start
Write-Host "  Waiting for ngrok to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Verify ngrok is running
Write-Host ""
Write-Host "[VERIFY] Verifying ngrok tunnel..." -ForegroundColor Cyan
$maxAttempts = 10
$attempt = 0
$tunnelFound = $false

while (-not $tunnelFound -and $attempt -lt $maxAttempts) {
    try {
        $ngrokApiUrl = "http://localhost:4040/api/tunnels"
        $tunnelInfo = Invoke-RestMethod -Uri $ngrokApiUrl -TimeoutSec 2 -ErrorAction Stop
        
        if ($tunnelInfo.tunnels -and $tunnelInfo.tunnels.Count -gt 0) {
            $tunnelFound = $true
            Write-Host "  ✓ Ngrok tunnel is active!" -ForegroundColor Green
            Write-Host ""
            
            foreach ($tunnel in $tunnelInfo.tunnels) {
                $publicUrl = $tunnel.public_url
                $config = $tunnel.config
                $addr = $config.addr
                
                Write-Host "  Tunnel Details:" -ForegroundColor Cyan
                Write-Host "    Public URL: $publicUrl" -ForegroundColor Green
                Write-Host "    Forwarding to: $addr" -ForegroundColor White
                
                if ($addr -match ":8000") {
                    Write-Host "    ✓ Correctly forwarding to port 8000" -ForegroundColor Green
                    
                    # Test the tunnel
                    Write-Host ""
                    Write-Host "  Testing tunnel..." -ForegroundColor Cyan
                    try {
                        $testUrl = $publicUrl.TrimEnd('/') + "/health"
                        $testResponse = Invoke-WebRequest -Uri $testUrl -TimeoutSec 10 -ErrorAction Stop
                        if ($testResponse.StatusCode -eq 200) {
                            Write-Host "    ✓ Tunnel is working!" -ForegroundColor Green
                            Write-Host ""
                            Write-Host "  ========================================" -ForegroundColor Green
                            Write-Host "  NGROK TUNNEL IS RUNNING!" -ForegroundColor Green
                            Write-Host "  ========================================" -ForegroundColor Green
                            Write-Host ""
                            Write-Host "  Public URL: $publicUrl" -ForegroundColor Cyan
                            Write-Host ""
                            Write-Host "  IMPORTANT: Update your .env file:" -ForegroundColor Yellow
                            Write-Host "    OAUTH_REDIRECT_BASE_URL=$publicUrl" -ForegroundColor White
                            Write-Host ""
                            Write-Host "  OAuth callback URLs to configure:" -ForegroundColor Yellow
                            Write-Host "    Instagram: $publicUrl/api/oauth/instagram/callback" -ForegroundColor White
                            Write-Host "    YouTube:   $publicUrl/api/oauth/youtube/callback" -ForegroundColor White
                            Write-Host "    TikTok:    $publicUrl/api/oauth/tiktok/callback" -ForegroundColor White
                            Write-Host ""
                            Write-Host "  Ngrok web interface: http://localhost:4040" -ForegroundColor Cyan
                            Write-Host ""
                        }
                    } catch {
                        Write-Host "    ⚠ Could not test tunnel (may need browser verification)" -ForegroundColor Yellow
                        Write-Host "    Try opening $publicUrl in your browser" -ForegroundColor Yellow
                    }
                }
            }
        }
    } catch {
        $attempt++
        if ($attempt -lt $maxAttempts) {
            Write-Host "  Waiting for ngrok to start... ($attempt/$maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $tunnelFound) {
    Write-Host "  ✗ Could not verify ngrok tunnel" -ForegroundColor Red
    Write-Host "  Check ngrok web interface: http://localhost:4040" -ForegroundColor Yellow
    Write-Host "  Or run: ngrok http 8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Ngrok is running in the background." -ForegroundColor Cyan
Write-Host "Keep this window open or ngrok will stop." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop ngrok" -ForegroundColor Yellow
Write-Host ""

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host ""
    Write-Host "Stopping ngrok..." -ForegroundColor Yellow
    $ngrokProcesses = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
    if ($ngrokProcesses) {
        foreach ($proc in $ngrokProcesses) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "Ngrok stopped." -ForegroundColor Green
}









