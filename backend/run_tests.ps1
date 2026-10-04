<#
.SYNOPSIS
    Runs the test suite for the Renewsys MES AI Chatbot backend.
#>

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Running Renewsys MES AI Chatbot Tests" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Run pytest
python -m pytest tests/ -v
