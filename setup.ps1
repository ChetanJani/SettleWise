$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'backend\.venv\Scripts\python.exe')) { python -m venv backend\.venv }
& '.\backend\.venv\Scripts\python.exe' -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency install failed.' }
Push-Location frontend
try { npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency install failed.' } } finally { Pop-Location }
Write-Output 'Ready. Run .\start.ps1'
