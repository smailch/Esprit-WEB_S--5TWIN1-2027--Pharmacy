# Vérifie qu'un clone NEUF fonctionne : clone (état commité) → installation → tests → lint/build → démarrage → /api/health.
# Usage (depuis Ahmed/) : .\scripts\check_clean_install.ps1 [-Source <url ou chemin du dépôt>] [-Branch <branche>]
param(
    [string]$Source = (git -C $PSScriptRoot rev-parse --show-toplevel),
    [string]$Branch = (git -C $PSScriptRoot rev-parse --abbrev-ref HEAD)
)
$ErrorActionPreference = "Continue"  # les avertissements npm/pip sur stderr ne sont pas des erreurs ; on teste $LASTEXITCODE
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("pharma-clean-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
function Step($msg) { Write-Host "`n=== $msg" -ForegroundColor Cyan }
function Check($what) { if ($LASTEXITCODE -ne 0) { Write-Host "ÉCHEC : $what" -ForegroundColor Red; exit 1 } }

Step "Clone de $Source ($Branch) dans $tmp"
git clone --quiet --branch $Branch $Source $tmp; Check "git clone"
$app = Join-Path $tmp "Ahmed"

Step "Installation (scripts/setup.ps1)"
& (Join-Path $app "scripts/setup.ps1"); Check "setup"

Step "Tests backend (pytest)"
Set-Location (Join-Path $app "backend")
& .venv/Scripts/python.exe -m pytest -q; Check "pytest"

Step "Build du projet React (site vitrine + ahmed.html)"
Set-Location $tmp
npm run build; Check "build"
if (-not (Test-Path (Join-Path $tmp "dist/ahmed.html"))) { Write-Host "ÉCHEC : dist/ahmed.html absent" -ForegroundColor Red; exit 1 }

Step "Démarrage de l'API et appel /api/health"
Set-Location (Join-Path $app "backend")
$server = Start-Process .venv/Scripts/python.exe -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8765" -PassThru -WindowStyle Hidden
try {
    $ok = $false
    for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
        Start-Sleep -Seconds 1
        try { $h = Invoke-RestMethod http://localhost:8765/api/health; $ok = $h.status -eq "ok" } catch { }
    }
    if (-not $ok) { Write-Host "ÉCHEC : /api/health ne répond pas" -ForegroundColor Red; exit 1 }
    Write-Host "health : $($h | ConvertTo-Json -Compress)"
    $r = Invoke-RestMethod http://localhost:8765/api/nlp/ask -Method Post -ContentType "application/json" `
        -Body '{"question":"Combien de patients enfants ?"}'
    Write-Host "NLP : $($r.message)"
} finally {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}

Set-Location $PSScriptRoot
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
Write-Host "`n✓ Installation propre validée" -ForegroundColor Green
