# PowerShell script to run tests on Windows
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root\..
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -m pytest -q
