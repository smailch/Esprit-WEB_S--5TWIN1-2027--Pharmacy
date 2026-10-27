# Lance scripts/load_ontology.py avec le Python du venv backend s'il existe.
Set-Location (Join-Path $PSScriptRoot "..")
$py = "backend/.venv/Scripts/python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py scripts/load_ontology.py @args
exit $LASTEXITCODE
