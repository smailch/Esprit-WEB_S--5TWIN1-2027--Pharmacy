# Lance le backend (nouvelle fenêtre) puis le frontend. Usage (depuis Ahmed/) : .\scripts\start.ps1
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root/backend'; .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000"
Write-Host "Backend : http://localhost:8000/docs  ·  Application : http://localhost:5174"
Set-Location "$root/frontend"
npm run dev
