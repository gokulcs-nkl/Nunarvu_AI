@echo off
rem Starts the Nunarvu AI backend, camera worker and web app, each in its own window.
rem Close a window (or press Ctrl+C in it) to stop that part.
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
start "Nunarvu AI - backend" cmd /k "cd backend && python manage.py runserver"
rem Give the backend a few seconds before the worker tries to reach it.
timeout /t 10 /nobreak >nul
start "Nunarvu AI - camera worker" cmd /k "cd backend && python manage.py run_camera_worker"
start "Nunarvu AI - web app" cmd /k "cd frontend && npm run dev"
echo Open http://localhost:5173 in your browser.
