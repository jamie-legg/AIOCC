# Start the simplified Upload Studio stack.

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AIOCC Upload Studio - Starting" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Root = Split-Path -Parent $PSScriptRoot
$UploadStudio = Join-Path $Root "upload-studio"

$Api = Start-Process -FilePath "uv" -ArgumentList @("run", "python", "-m", "uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000") -WorkingDirectory $Root -PassThru
$Ui = Start-Process -FilePath "npm" -ArgumentList @("run", "dev") -WorkingDirectory $UploadStudio -PassThru

Write-Host "[API] http://localhost:8000" -ForegroundColor Blue
Write-Host "[UI]  http://localhost:5173" -ForegroundColor Magenta
Write-Host ""
Write-Host "Press Ctrl+C to stop. Child processes may need to be closed from Task Manager if PowerShell is interrupted." -ForegroundColor Yellow

try {
    while (-not $Api.HasExited -and -not $Ui.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    if (-not $Api.HasExited) { Stop-Process -Id $Api.Id -Force }
    if (-not $Ui.HasExited) { Stop-Process -Id $Ui.Id -Force }
}
