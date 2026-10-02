param([string]$Helper, [string]$Root, [string]$Scenario)
$ErrorActionPreference = 'Stop'
. $Helper
$env:LOCALAPPDATA = Join-Path $Root 'apps with spaces'
$env:TEMP = Join-Path $Root 'temp'
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
$env:ESPANSR_NO_ESPANSO = ''
$global:events = @()
$global:installed = $Scenario -ne 'missing'
$global:version = [Version]'2.3.0'
if ($Scenario -eq 'current') { $global:version = [Version]'2.4.1' }
if ($Scenario -eq 'newer') { $global:version = [Version]'2.5.0' }
if ($Scenario -eq 'unknown') { $global:version = $null }
if ($Scenario -eq 'env-optout') { $env:ESPANSR_NO_ESPANSO = '1' }
function Find-Espanso {
    if (-not $global:installed) { return $null }
    if ($Scenario -eq 'custom') { return (Join-Path $Root 'custom\espansod.exe') }
    return (Join-Path $env:LOCALAPPDATA 'Programs\Espanso\espansod.exe')
}
function Get-EspansoRuntimeVersion { param($Executable) return $global:version }
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec)
    $global:events += 'download'
    if ($Scenario -eq 'network-failure') { throw 'synthetic network failure' }
    Set-Content -LiteralPath $OutFile -Value 'synthetic verified installer'
}
function Get-EspansoInstallerHash {
    param($Path)
    $hash = $EspansoInstallerSha256
    if ($Scenario -eq 'bad-hash') { $hash = 'wrong' }
    return $hash
}
function Start-Process {
    param($FilePath, $ArgumentList, [switch]$PassThru, $WindowStyle)
    if ($WindowStyle -ne 'Hidden') { throw 'Unexpected visible helper' }
    $code = 0
    if ($ArgumentList -contains 'stop') { $global:events += 'stop' }
    else {
        if ($ArgumentList -notcontains '/VERYSILENT' -or $ArgumentList -notcontains '/NORESTART') {
            throw 'Unexpected installer flags'
        }
        $global:events += 'install'
        if ($Scenario -eq 'installer-failure') { $code = 1 }
        elseif ($Scenario -ne 'stale-path') {
            $global:version = [Version]'2.4.1'
            $global:installed = $true
        }
    }
    $process = [PSCustomObject]@{ ExitCode = $code }
    $process | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value { param($Millis) return $true }
    $process | Add-Member -MemberType ScriptMethod -Name Dispose -Value { }
    return $process
}
$result = Ensure-EspansoRuntime -NoEspanso:($Scenario -eq 'flag-optout')
@{ executable = $result; events = @($global:events); version = "$global:version"; remaining = @(Get-ChildItem -LiteralPath $env:TEMP).Count } | ConvertTo-Json -Compress
