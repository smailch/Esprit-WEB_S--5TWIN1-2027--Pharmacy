@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist "backend\.venv\Scripts\python.exe" (echo Lancez d'abord scripts\setup.bat & exit /b 1)
echo Demarrage de l'API (http://localhost:8000/docs) et du site (http://localhost:5173)...
start "PharmaSemantique API" cmd /k ""backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --port 8000"
timeout /t 6 /nobreak >nul
start "" http://localhost:5173
call npm run dev
