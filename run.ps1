# Caixa Postal 41 — iniciar servidor web
# Uso: .\run.ps1
Set-Location $PSScriptRoot
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8765 --reload
