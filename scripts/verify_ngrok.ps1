# Verify ngrok tunnel is running and working
# This script checks if ngrok is properly configured and accessible

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NGROK TUNNEL VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if API is running
Write-Host "[1/4] Checking if API server is running..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ API server is running on port 8000" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ API server is NOT running on port 8000" -ForegroundColor Red
    Write-Host "  Please start the API server first" -ForegroundColor Yellow
    exit 1
}

# Check ngrok configuration
Write-Host ""
Write-Host "[2/4] Checking ngrok configuration..." -ForegroundColor Cyan
$ngrokToken = $env:NGROK_AUTH_TOKEN
if ($ngrokToken) {
    Write-Host "  ✓ NGROK_AUTH_TOKEN is set" -ForegroundColor Green
} else {
    Write-Host "  ⚠ NGROK_AUTH_TOKEN not set" -ForegroundColor Yellow
}

$ngrokDomain = $env:NGROK_DOMAIN
if ($ngrokDomain) {
    Write-Host "  ✓ NGROK_DOMAIN is set: $ngrokDomain" -ForegroundColor Green
} else {
    Write-Host "  ℹ NGROK_DOMAIN not set" -ForegroundColor Yellow
}

$oauthBaseUrl = $env:OAUTH_REDIRECT_BASE_URL
if ($oauthBaseUrl) {
    Write-Host "  ✓ OAUTH_REDIRECT_BASE_URL is set: $oauthBaseUrl" -ForegroundColor Green
} else {
    Write-Host "  ⚠ OAUTH_REDIRECT_BASE_URL not set" -ForegroundColor Yellow
    Write-Host "    This is required for OAuth to work!" -ForegroundColor Red
}

# Check ngrok API
Write-Host ""
Write-Host "[3/4] Checking ngrok tunnel status..." -ForegroundColor Cyan
try {
    $ngrokApiUrl = "http://localhost:4040/api/tunnels"
    $tunnelInfo = Invoke-RestMethod -Uri $ngrokApiUrl -TimeoutSec 2 -ErrorAction Stop
    
    if ($tunnelInfo.tunnels -and $tunnelInfo.tunnels.Count -gt 0) {
        Write-Host "  ✓ Found $($tunnelInfo.tunnels.Count) active tunnel(s)" -ForegroundColor Green
        Write-Host ""
        
        foreach ($tunnel in $tunnelInfo.tunnels) {
            $publicUrl = $tunnel.public_url
            $config = $tunnel.config
            $addr = $config.addr
            $proto = $tunnel.proto
            
            Write-Host "  Tunnel Details:" -ForegroundColor Cyan
            Write-Host "    Protocol: $proto" -ForegroundColor White
            Write-Host "    Public URL: $publicUrl" -ForegroundColor Cyan
            Write-Host "    Forwarding to: $addr" -ForegroundColor White
            
            # Verify the tunnel points to port 8000
            if ($addr -match ":8000") {
                Write-Host "    ✓ Tunnel correctly points to port 8000" -ForegroundColor Green
                
                # Test the public URL
                Write-Host ""
                Write-Host "[4/4] Testing public URL accessibility..." -ForegroundColor Cyan
                try {
                    $testUrl = $publicUrl.TrimEnd('/') + "/health"
                    Write-Host "    Testing: $testUrl" -ForegroundColor Yellow
                    $testResponse = Invoke-WebRequest -Uri $testUrl -TimeoutSec 10 -ErrorAction Stop
                    
                    if ($testResponse.StatusCode -eq 200) {
                        Write-Host ""
                        Write-Host "  ========================================" -ForegroundColor Green
                        Write-Host "  ✓ NGROK TUNNEL IS WORKING!" -ForegroundColor Green
                        Write-Host "  ========================================" -ForegroundColor Green
                        Write-Host ""
                        Write-Host "  Public URL: $publicUrl" -ForegroundColor Cyan
                        Write-Host ""
                        Write-Host "  IMPORTANT: Make sure your .env file has:" -ForegroundColor Yellow
                        Write-Host "    OAUTH_REDIRECT_BASE_URL=$publicUrl" -ForegroundColor White
                        Write-Host ""
                        Write-Host "  OAuth callback URLs:" -ForegroundColor Yellow
                        Write-Host "    Instagram: $publicUrl/api/oauth/instagram/callback" -ForegroundColor White
                        Write-Host "    YouTube:   $publicUrl/api/oauth/youtube/callback" -ForegroundColor White
                        Write-Host "    TikTok:    $publicUrl/api/oauth/tiktok/callback" -ForegroundColor White
                        Write-Host ""
                    } else {
                        Write-Host "    ✗ Public URL returned status: $($testResponse.StatusCode)" -ForegroundColor Red
                    }
                } catch {
                    $errorMsg = $_.Exception.Message
                    Write-Host "    ✗ Could not access public URL" -ForegroundColor Red
                    Write-Host "    Error: $errorMsg" -ForegroundColor Red
                    
                    if ($errorMsg -match "403" -or $errorMsg -match "Forbidden") {
                        Write-Host ""
                        Write-Host "    This is likely ngrok's browser verification page." -ForegroundColor Yellow
                        Write-Host "    Try opening $publicUrl in your browser first to verify." -ForegroundColor Yellow
                    }
                }
            } else {
                Write-Host "    ⚠ Tunnel does not point to port 8000" -ForegroundColor Yellow
                Write-Host "    Current target: $addr" -ForegroundColor Yellow
                Write-Host "    Expected: localhost:8000" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  ✗ No active ngrok tunnels found" -ForegroundColor Red
        Write-Host ""
        Write-Host "  To start ngrok manually, run:" -ForegroundColor Yellow
        Write-Host "    ngrok http 8000" -ForegroundColor White
        Write-Host ""
        Write-Host "  Or if you have a reserved domain:" -ForegroundColor Yellow
        Write-Host "    ngrok http 8000 --domain=your-domain.ngrok-free.dev" -ForegroundColor White
    }
} catch {
    Write-Host "  ✗ Could not connect to ngrok API (http://localhost:4040)" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  This means ngrok is not running." -ForegroundColor Yellow
    Write-Host "  To start ngrok, run:" -ForegroundColor Yellow
    Write-Host "    ngrok http 8000" -ForegroundColor White
    Write-Host ""
    Write-Host "  Or install pyngrok and it will start automatically." -ForegroundColor Yellow
}

Write-Host ""









