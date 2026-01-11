Param(
  [string]$PythonExe = "",
  [string]$OutDir = ""
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$BackendDir = Join-Path $RepoRoot 'backend'
$Entry = Join-Path $BackendDir 'native_host_entry.py'

if (-not (Test-Path $Entry)) {
  throw "Entry script not found: $Entry"
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  $PythonExe = (Join-Path $RepoRoot 'WinPython\WPy64-313110\python\python.exe')
}

if (-not (Test-Path $PythonExe)) {
  throw "Python not found: $PythonExe"
}

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = (Join-Path $BackendDir 'host')
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "[MailSorter] Building native host exe..."
Write-Host "  Python: $PythonExe"
Write-Host "  Entry : $Entry"
Write-Host "  Out   : $OutDir"

& $PythonExe -m pip install -U pyinstaller | Out-Host

$PyInstallerParams = @(
  '-m','PyInstaller',
  '--clean',
  '--noconfirm',
  '--name','mailsorter-host',
  '--distpath', $OutDir,
  '--workpath', (Join-Path $OutDir 'build'),
  '--specpath', $OutDir
)

$PyInstallerParams += '--onefile'

$PyInstallerParams += $Entry

& $PythonExe @PyInstallerParams | Out-Host

$Exe = Join-Path $OutDir 'mailsorter-host.exe'
if (-not (Test-Path $Exe)) {
  throw "Build succeeded but exe not found at: $Exe"
}

Write-Host "[MailSorter] Built: $Exe"
