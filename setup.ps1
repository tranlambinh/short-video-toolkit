# Windows setup:  powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Need($cmd, $hint) { if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host "Missing: $cmd. $hint" -ForegroundColor Red; exit 1 } }

Write-Host "1/6 Checking tools" -ForegroundColor Cyan
Need "python" "Install Python 3.10-3.12 from python.org (tick 'Add to PATH')."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "ffmpeg not found; installing with winget ..."
  winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
  Write-Host "Open a NEW PowerShell window and run this script again so ffmpeg is on PATH." -ForegroundColor Yellow; exit 0
}
Need "docker" "Install Docker Desktop from docker.com and start it."

Write-Host "2/6 Python environment (.venv)" -ForegroundColor Cyan
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "3/6 Browser for /news-video (skipped if Chrome is installed)" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m playwright install chromium

Write-Host "4/6 Speech models (Whisper medium, about 1.5 GB)" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe setup_models.py --piper

Write-Host "5/6 Settings" -ForegroundColor Cyan
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env. Open it and paste your free Pexels key (pexels.com/api)." -ForegroundColor Yellow }
New-Item -ItemType Directory -Force assets\music, work, videos | Out-Null

Write-Host "6/6 Docker image for stock footage" -ForegroundColor Cyan
docker compose pull

Write-Host "`nChecking everything:" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe check.py
Write-Host "`nNext: add a royalty-free .mp3 to assets\music, then every time:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1`n  claude"
