<#
.SYNOPSIS
    Runs the Renewsys MES AI Chatbot backend server.
#>

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Renewsys MES AI Chatbot Backend Startup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    . ".\venv\Scripts\Activate.ps1"
}

# 1. Ensure .env exists
if (-not (Test-Path ".env")) {
    Write-Host "No .env file found. Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. Please review the configuration." -ForegroundColor Green
}

# 2. Check for data directory (for SQLite DB)
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# 3. Initialize Admin User
Write-Host "`nChecking/Initializing Admin User..." -ForegroundColor Cyan
python init_admin.py

# 4. Start Server
Write-Host "`nStarting FastAPI server..." -ForegroundColor Cyan
Write-Host "Access the API documentation at: http://localhost:8080/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server.`n" -ForegroundColor Yellow

python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
