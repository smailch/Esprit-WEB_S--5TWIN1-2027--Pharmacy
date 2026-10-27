# Lance mon backend (port 8001, nouvelle fenêtre) puis le projet React commun.
# Usage (depuis Ahmed/) : .\scripts\start.ps1   → http://localhost:5173/ahmed.html
$ahmed = Resolve-Path (Join-Path $PSScriptRoot "..")
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$ahmed/backend'; .venv/Scripts/python.exe -m uvicorn app.main:app --port 8001"
Write-Host "API : http://localhost:8001/docs  ·  Application : http://localhost:5173/ahmed.html"
Set-Location (Join-Path $ahmed "..")
npm run dev
