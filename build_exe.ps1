$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller --disable-pip-version-check
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --name WasteWiseAI --add-data "app;app" --add-data "data;data" --workpath build-wastewise --distpath dist-real-dataset launcher.py
Write-Host "Built: $root\dist-real-dataset\WasteWiseAI\WasteWiseAI.exe"
