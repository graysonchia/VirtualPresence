$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $PSScriptRoot
$ProjectDir = Split-Path -Parent $BackendDir

Write-Host "Creating Python environment..."
Set-Location $BackendDir
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Downloading YuNet and SFace models..."
.\.venv\Scripts\python.exe scripts\download_face_models.py

Write-Host "Checking PostgreSQL..."
$env:PGPASSWORD = "rodolfo"
$DatabaseExists = psql -U postgres -h localhost -tAc "SELECT 1 FROM pg_database WHERE datname='virtualpresence'"
if ($LASTEXITCODE -ne 0) {
    throw "Could not connect to PostgreSQL with the configured credentials."
}
$DatabaseExistsText = ($DatabaseExists | Out-String).Trim()
if ($DatabaseExistsText -ne "1") {
    createdb -U postgres -h localhost virtualpresence
}

Write-Host "Applying Alembic migrations..."
.\.venv\Scripts\python.exe -m alembic upgrade head

Write-Host "Installing frontend dependencies..."
Set-Location "$ProjectDir\frontend"
npm.cmd install

Write-Host "VirtualPresence setup complete."
