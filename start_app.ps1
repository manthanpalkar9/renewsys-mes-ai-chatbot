<#
.SYNOPSIS
    Starts both the backend and frontend for the Renewsys MES AI Chatbot locally.
#>

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Starting Renewsys MES AI Chatbot" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Start Backend
Write-Host "Starting Backend..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd backend; .\run.ps1" -PassThru

# Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -PassThru

Write-Host "`nBoth processes have been started in separate windows." -ForegroundColor Yellow
Write-Host "Backend API: http://localhost:8080/docs"
Write-Host "Frontend UI: http://localhost:5173"
