@echo off
call venv\Scripts\activate.bat
python -c "from config import settings; import subprocess, sys; raise SystemExit(subprocess.call([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', str(settings.app_port), '--reload']))"
