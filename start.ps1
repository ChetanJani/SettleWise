param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run setup.ps1 first.' }
$npmPath = (Get-Command npm.cmd).Source
foreach ($service in @(@{Name='backend';Port=8001},@{Name='frontend';Port=5174})) {
  if (Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $($service.Port) is already in use. Stop the existing app first." }
}
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8001' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'backend.log') -RedirectStandardError (Join-Path $runtimeDir 'backend-error.log') -PassThru
$frontendProcess = Start-Process -FilePath $npmPath -ArgumentList 'run dev' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend-error.log') -PassThru
@{Backend=$backendProcess.Id;Frontend=$frontendProcess.Id;BackendStarted=$backendProcess.StartTime.ToUniversalTime().ToString('o');FrontendStarted=$frontendProcess.StartTime.ToUniversalTime().ToString('o');Root=$projectRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'processes.json')
Write-Output 'SettleWise: http://127.0.0.1:5174'
Write-Output 'Backend API: http://127.0.0.1:8001/docs'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5174' }
