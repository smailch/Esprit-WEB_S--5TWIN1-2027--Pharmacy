# Installation complète (Windows) : venv Python, dépendances épinglées, modèles NLP, dépendances front.
# Usage (depuis Ahmed/) : .\scripts\setup.ps1
$ErrorActionPreference = "Continue"  # les avertissements npm/pip sur stderr ne sont pas des erreurs ; on teste $LASTEXITCODE
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Set-Location backend
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
& .venv/Scripts/python.exe -m pip install --quiet --upgrade pip
& .venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }
& .venv/Scripts/python.exe scripts/setup_models.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Set-Location ../frontend
npm ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "`nInstallation terminée. Lancer : .\scripts\start.ps1"
