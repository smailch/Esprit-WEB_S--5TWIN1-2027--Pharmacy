@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo === PharmaSemantique : installation ===

where python >nul 2>nul || (echo [ERREUR] Python 3.11+ introuvable. Installez-le depuis https://www.python.org/downloads/ en cochant "Add to PATH". & exit /b 1)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || (echo [ERREUR] Python 3.11 ou plus recent requis. & exit /b 1)
where npm >nul 2>nul || (echo [ERREUR] Node.js 18+ introuvable. Installez-le depuis https://nodejs.org/ & exit /b 1)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/3] Creation de l'environnement Python...
  python -m venv backend\.venv || exit /b 1
)
echo [2/3] Installation des dependances Python (dont spaCy fr_core_news_sm)...
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip -q
"backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || exit /b 1

echo [3/3] Installation des dependances front-end...
call npm install --no-audit --no-fund || exit /b 1

echo.
echo Installation terminee. Lancez : scripts\start.bat
endlocal
