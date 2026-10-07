$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '.local\processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No recorded SettleWise processes.'; exit }
$state = Get-Content -LiteralPath $statePath | ConvertFrom-Json
if ([IO.Path]::GetFullPath($state.Root) -ne [IO.Path]::GetFullPath($PSScriptRoot)) { throw 'Process record does not belong to this project.' }
$processes = @(Get-CimInstance Win32_Process)
$targets = @()
foreach ($serviceName in @('Backend','Frontend')) {
  $process = Get-Process -Id ([int]$state.$serviceName) -ErrorAction SilentlyContinue
  $recordedStart = $state.($serviceName+'Started')
  if ($process -and $recordedStart -and $process.StartTime.ToUniversalTime().Ticks -eq ([datetime]$recordedStart).ToUniversalTime().Ticks) { $targets += $process.Id }
}
for ($depth=0; $depth -lt 6; $depth++) { $targets += @($processes | Where-Object { $_.ParentProcessId -in $targets } | Select-Object -ExpandProperty ProcessId); $targets=@($targets | Select-Object -Unique) }
foreach ($pidToStop in ($targets | Sort-Object -Descending)) { Stop-Process -Id $pidToStop -Force -ErrorAction SilentlyContinue }
Remove-Item -LiteralPath $statePath
Write-Output 'SettleWise services stopped.'
