Param(
  [string]$RepoRoot = ""
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
}

$Exe = Join-Path $RepoRoot 'backend\host\mailsorter-host.exe'
if (-not (Test-Path $Exe)) {
  throw "Native host exe not found: $Exe`nBuild it first: powershell -ExecutionPolicy Bypass -File scripts\build_native_host_windows.ps1"
}

$OutDir = Join-Path $env:LOCALAPPDATA 'MailSorter'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ManifestPath = Join-Path $OutDir 'com.mailsorter.backend.json'

$manifest = [ordered]@{
  name = 'com.mailsorter.backend'
  description = 'MailSorter Native Backend'
  path = $Exe
  type = 'stdio'
  allowed_extensions = @('mailsorter@planv5.local')
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path $ManifestPath

$RegKey = 'HKCU:\Software\Mozilla\NativeMessagingHosts\com.mailsorter.backend'
New-Item -Force -Path $RegKey | Out-Null
Set-ItemProperty -Path $RegKey -Name '(default)' -Value $ManifestPath

Write-Host "SUCCESS: Registered Native Messaging Host" -ForegroundColor Green
Write-Host "  Exe     : $Exe"
Write-Host "  Manifest: $ManifestPath"
Write-Host "  Registry: HKCU\Software\Mozilla\NativeMessagingHosts\com.mailsorter.backend"
Write-Host "Restart Thunderbird/Betterbird to apply changes."
