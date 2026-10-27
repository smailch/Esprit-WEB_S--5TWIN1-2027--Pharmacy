# Lance scripts/eval_nlp.py avec le Python du venv backend s'il existe.
Set-Location (Join-Path $PSScriptRoot "..")
$py = "backend/.venv/Scripts/python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py scripts/eval_nlp.py @args
exit $LASTEXITCODE
