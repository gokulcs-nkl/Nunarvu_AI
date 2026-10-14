@echo off
rem Starts the Nunarvu AI backend, camera worker and web app, each in its own window.
rem Close a window (or press Ctrl+C in it) to stop that part.
cd /d "%~dp0"
set PYTHONUNBUFFERED=1

rem Machine-specific steps (for example starting a local database) go in local_start.bat.
if exist local_start.bat (
  call local_start.bat
  if errorlevel 1 exit /b 1
)

rem Python to use: the path in python_path.txt if that file exists, otherwise "python".
set "PY=python"
if exist python_path.txt set /p PY=<python_path.txt
echo Using Python: %PY%
"%PY%" --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Could not run Python at: %PY%
  echo Check the path in python_path.txt, or delete that file to use "python" from PATH.
  pause
  exit /b 1
)

start "Nunarvu AI - backend" cmd /k "cd backend && "%PY%" manage.py runserver"
rem Give the backend a few seconds before the worker tries to reach it.
timeout /t 10 /nobreak >nul
start "Nunarvu AI - camera worker" cmd /k "cd backend && "%PY%" manage.py run_camera_worker"
start "Nunarvu AI - web app" cmd /k "cd frontend && npm run dev"
echo Open http://localhost:5173 in your browser.
