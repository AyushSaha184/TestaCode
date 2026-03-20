:: This file starts backend and frontend services for local development.
:: Run this file with ".\server.bat" from terminal.

@echo off
setlocal

echo ===================================================
echo        AI-Test-Gen Local Startup
echo ===================================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

:: 0. Stop stale backend Python processes on port 8000
echo [0/3] Stopping stale backend processes...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping process on port 8000 PID %%P
    taskkill /PID %%P /F >nul 2>&1
)
echo Port 8000 cleanup complete.
echo.

:: 1. Validate prerequisites
echo [1/3] Checking local prerequisites...
if not exist "%ROOT%\.venv\Scripts\activate.bat" (
    echo .venv was not found at "%ROOT%\.venv".
    echo Create it first with: python -m venv .venv
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found on PATH. Install Node.js and try again.
    exit /b 1
)
echo Prerequisites look good.
echo.

:: 2. Start Backend Server
echo [2/3] Starting FastAPI Backend on port 8000...
start "AI-Test-Gen Backend" cmd /k "cd /d ""%ROOT%"" && call "".venv\Scripts\activate.bat"" && python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul
echo Backend started in a new window.
echo.

:: 3. Start Frontend Server
echo [3/3] Starting Frontend on port 5173...
start "AI-Test-Gen Frontend" cmd /k "cd /d ""%ROOT%\frontend"" && npm run dev"
echo Frontend started in a new window.
echo.

echo ===================================================
echo All services have been launched!
echo - Frontend: http://localhost:5173
echo - Backend API: http://localhost:8000/docs
echo ===================================================
echo.
if not defined CI pause

endlocal
