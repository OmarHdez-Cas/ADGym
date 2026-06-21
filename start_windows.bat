@echo off
echo Iniciando Santa Fuerza App (Windows)...
cd %~dp0

IF NOT EXIST venv (
    echo Configurando entorno por primera vez...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

echo Iniciando servidor...
start http://localhost:5000
python app.py
pause
