Param(
  [string]$HostExePath = "",
  [string]$ExtensionId = "mailsorter@planv5.local"
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$DefaultHost = Join-Path $RepoRoot 'backend\host\mailsorter-host.exe'

if ([string]::IsNullOrWhiteSpace($HostExePath)) {
  $HostExePath = $DefaultHost
}

if (-not (Test-Path $HostExePath)) {
  Write-Host "ERROR: Native host exe not found at: $HostExePath"
  Write-Host "Build it first (dev):"
  Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\\build_native_host_windows.ps1"
  exit 1
}

$InstallDir = Join-Path $env:LOCALAPPDATA 'MailSorter\native-host'
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$InstalledExe = Join-Path $InstallDir 'mailsorter-host.exe'
Copy-Item -Force $HostExePath $InstalledExe

$ManifestDir = Join-Path $env:LOCALAPPDATA 'MailSorter\native-messaging'
New-Item -ItemType Directory -Force -Path $ManifestDir | Out-Null

$ManifestPath = Join-Path $ManifestDir 'com.mailsorter.backend.json'

$Manifest = @{
  name = 'com.mailsorter.backend'
  description = 'MailSorter Native Backend'
  path = $InstalledExe
  type = 'stdio'
  allowed_extensions = @($ExtensionId)
}

$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ManifestPath

$RegKey = 'HKCU:\\Software\\Mozilla\\NativeMessagingHosts\\com.mailsorter.backend'
New-Item -Force -Path $RegKey | Out-Null
Set-ItemProperty -Path $RegKey -Name '(default)' -Value $ManifestPath

Write-Host "[MailSorter] Installed native host: $InstalledExe"
Write-Host "[MailSorter] Wrote manifest: $ManifestPath"
Write-Host "[MailSorter] Registered: $RegKey"
Write-Host "Restart Thunderbird/Betterbird."
