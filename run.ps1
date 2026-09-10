$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt --disable-pip-version-check
Start-Process "http://127.0.0.1:8000"
& .\.venv\Scripts\python.exe launcher.py
