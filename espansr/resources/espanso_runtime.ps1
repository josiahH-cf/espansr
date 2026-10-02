# Shared native Windows and WSL-hosted Espanso installation/upgrade.
# The official per-user installer preserves configuration outside its app folder.
$EspansoMinimumVersion = [Version]'2.4.1'
$EspansoInstallerUrl = 'https://github.com/espanso/espanso/releases/download/v2.4.1/Espanso-Win-Installer-x86_64.exe'
$EspansoInstallerSha256 = '995c9c8ae9df4b1c464caa2595e478ed35521e1433f95d0945eed8ecbfc7a1f2'

function Find-Espanso {
    $cmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        $cmdDir = Split-Path -Parent $cmd.Source
        $daemon = Join-Path $cmdDir 'espansod.exe'
        if (Test-Path -LiteralPath $daemon) { return $daemon }
        return $cmd.Source
    }
    foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles)) {
        if (-not $base) { continue }
        $folder = if ($base -eq $env:LOCALAPPDATA) { 'Programs\Espanso' } else { 'Espanso' }
        foreach ($name in @('espansod.exe', 'espanso.CMD', 'espanso.exe')) {
            $candidate = Join-Path (Join-Path $base $folder) $name
            if (Test-Path -LiteralPath $candidate) { return $candidate }
        }
    }
    return $null
}

function Get-EspansoRuntimeVersion {
    param([string]$Executable)
    if (-not $Executable -or [IO.Path]::GetExtension($Executable) -ine '.exe') { return $null }
    $process = New-Object System.Diagnostics.Process
    try {
        $process.StartInfo.FileName = $Executable
        $process.StartInfo.Arguments = '--version'
        $process.StartInfo.UseShellExecute = $false
        $process.StartInfo.CreateNoWindow = $true
        $process.StartInfo.RedirectStandardOutput = $true
        $process.StartInfo.RedirectStandardError = $true
        [void]$process.Start()
        $output = $process.StandardOutput.ReadToEndAsync()
        $errors = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(5000)) { $process.Kill(); return $null }
        # Espanso 2.3 prints its valid version but exits 1; 2.4 fixed this.
        $text = $output.Result.Trim()
        if ($text -match '^(?:espanso\s+)?(\d+\.\d+\.\d+)$') { return [Version]$Matches[1] }
    }
    catch { return $null }
    finally { $process.Dispose() }
    return $null
}

function Ensure-EspansoRuntime {
    param([switch]$NoEspanso)
    $existing = Find-Espanso
    if ($NoEspanso -or $env:ESPANSR_NO_ESPANSO -eq '1') {
        Write-Host '[INFO] Skipping Espanso installation/upgrade (-NoEspanso / ESPANSR_NO_ESPANSO=1)'
        return $existing
    }
    $version = Get-EspansoRuntimeVersion -Executable $existing
    if ($version -and $version -ge $EspansoMinimumVersion) {
        Write-Host "[ OK ] Espanso $version already meets $EspansoMinimumVersion; no upgrade needed"
        return $existing
    }
    if ($existing -and -not $version) {
        Write-Host '[WARN] Could not verify Espanso version; keeping the existing installation. Upgrade it manually for counters.'
        return $existing
    }
    # Avoid silently replacing an unrelated portable/custom installation.
    $userInstall = Join-Path $env:LOCALAPPDATA 'Programs\Espanso'
    if ($existing -and (Split-Path -Parent $existing).TrimEnd('\') -ine $userInstall.TrimEnd('\')) {
        Write-Host '[WARN] Custom/system Espanso installation detected. Upgrade through its original installer to 2.4.1+.'
        return $existing
    }
    if (-not [Environment]::Is64BitOperatingSystem) {
        Write-Host '[WARN] The official Espanso installer requires 64-bit Windows; keeping espansr usable without counters.'
        return $existing
    }
    $download = Join-Path ([IO.Path]::GetTempPath()) ('espansr-espanso-' + [Guid]::NewGuid().ToString('N') + '.exe')
    try {
        Write-Host "[INFO] Installing/upgrading Espanso to $EspansoMinimumVersion (official per-user installer)..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $EspansoInstallerUrl -OutFile $download -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
        if ((Get-FileHash -LiteralPath $download -Algorithm SHA256 -ErrorAction Stop).Hash -ine $EspansoInstallerSha256) {
            throw 'Espanso installer checksum did not match the verified release'
        }
        # Download and verify first, so network errors do not stop a working daemon.
        if ($existing) {
            $stop = Start-Process -FilePath $existing -ArgumentList 'service', 'stop' -PassThru -WindowStyle Hidden
            try {
                if (-not $stop.WaitForExit(10000)) { throw 'Espanso service stop timed out' }
            }
            finally { $stop.Dispose() }
        }
        $setup = Start-Process -FilePath $download -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', ('/DIR="' + $userInstall + '"') -PassThru -WindowStyle Hidden
        try {
            if (-not $setup.WaitForExit(180000)) { throw 'Espanso installer timed out; check its process before retrying' }
            if ($setup.ExitCode -ne 0) { throw "Espanso installer exited $($setup.ExitCode)" }
        }
        finally { $setup.Dispose() }
        $installed = Find-Espanso
        $installedVersion = Get-EspansoRuntimeVersion -Executable $installed
        if (-not $installedVersion -or $installedVersion -lt $EspansoMinimumVersion) {
            throw 'Espanso upgrade could not be verified; a stale PATH entry may select an older copy'
        }
        Write-Host "[ OK ] Verified Espanso $installedVersion"
        return $installed
    }
    catch {
        Write-Host "[WARN] Espanso installation/upgrade did not complete: $($_.Exception.Message)"
        Write-Host '[INFO] Install Espanso 2.4.1+ from https://espanso.org, then rerun espansr setup. Existing templates remain usable.'
        return (Find-Espanso)
    }
    finally {
        if (Test-Path -LiteralPath $download) {
            try { Remove-Item -LiteralPath $download -Force -ErrorAction Stop }
            catch { Write-Host "[WARN] Could not remove downloaded installer: $download" }
        }
    }
}
