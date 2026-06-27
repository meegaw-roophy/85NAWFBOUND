<#
PowerShell helper to prepare and start the development environment on Windows.
Usage: Open PowerShell as Administrator and run:
  .\scripts\dev_start.ps1

This will:
- copy `.env.example` to `.env` if missing
- open `.env` for you to edit
- bring up docker compose services
- install backend deps (optional)
- run Alembic migrations
- start the backend with uvicorn (foreground)
#>

param(
    [switch]$SkipDeps
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# ensure .env
$envPath = Join-Path $root '..\.env'
$envExample = Join-Path $root '..\.env.example'
if (-not (Test-Path $envPath)) {
    Copy-Item $envExample $envPath
    Write-Host "Copied .env.example -> .env"
}

Write-Host "Opening .env in notepad. Please set STRIPE_API_KEY and STRIPE_WEBHOOK_SECRET if needed. Save and close to continue."
Start-Process notepad $envPath -Wait

Write-Host "Starting docker compose..."
docker compose up -d

Push-Location ..\backend

if (-not $SkipDeps) {
    Write-Host "Installing backend requirements (this may take a while)..."
    python -m pip install -r requirements.txt
}

Write-Host "Running Alembic migrations..."
if (Test-Path .\scripts\run_migrations.sh) {
    # If bash script exists, run via bash if available
    if (Get-Command bash -ErrorAction SilentlyContinue) {
        bash .\scripts\run_migrations.sh
    } else {
        Write-Host "No bash available; running alembic via python module"
        python -m alembic upgrade head
    }
} else {
    python -m alembic upgrade head
}

Write-Host "Starting backend (uvicorn) on port 8000..."
uvicorn app.main:app --reload --port 8000

Pop-Location
