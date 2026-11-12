# Native Windows bootstrap. No activation, downloads or execution-policy changes.
$ErrorActionPreference = 'Stop'
$runtimeRoot = Split-Path -Parent $PSScriptRoot
$probeCode = 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'

function Test-AidlcPython([string]$Executable, [string]$Prefix = '') {
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = $Executable
    $process.StartInfo.Arguments = ($Prefix + ' -c "' + $probeCode + '"').Trim()
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    try {
        [void]$process.Start()
        if (-not $process.WaitForExit(5000)) {
            $process.Kill()
            return $false
        }
        return $process.ExitCode -eq 0
    } catch {
        return $false
    } finally {
        $process.Dispose()
    }
}

$candidates = @()
if ($env:AIDLC_PYTHON) { $candidates += ,@($env:AIDLC_PYTHON, '') }
$candidates += ,@((Join-Path $runtimeRoot '.venv/Scripts/python.exe'), '')
if ($env:VIRTUAL_ENV) {
    $candidates += ,@((Join-Path $env:VIRTUAL_ENV 'Scripts/python.exe'), '')
}
foreach ($name in @('python', 'py', 'python3')) {
    $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
    if ($command) {
        $prefix = if ($name -eq 'py') { '-3' } else { '' }
        $candidates += ,@($command.Source, $prefix)
    }
}

foreach ($candidate in $candidates) {
    # Windows Store aliases can open UI instead of executing Python.
    if ($candidate[0] -match '[\\/]WindowsApps[\\/]') { continue }
    if (Test-AidlcPython $candidate[0] $candidate[1]) {
        # Encode argv so Windows PowerShell 5.1 cannot drop empty arguments or
        # alter quotes in -c code during native-command argument serialization.
        # Get-Content strings carry PowerShell ETS metadata. Serializing those
        # wrappers directly produces JSON objects instead of argv strings.
        # ToString() returns plain text while retaining empty CLI arguments.
        $plainArgs = @(
            foreach ($argument in $args) {
                if ($null -eq $argument) { '' } else { $argument.ToString() }
            }
        )
        $json = ConvertTo-Json -InputObject $plainArgs -Compress
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
        $bootstrapArgs = @()
        if ($candidate[1]) { $bootstrapArgs += $candidate[1] }
        $bootstrapArgs += @((Join-Path $PSScriptRoot 'factory_python.py'), '--encoded-args', $encoded)
        & $candidate[0] @bootstrapArgs
        exit $LASTEXITCODE
    }
}
[Console]::Error.WriteLine('[AIDLC Python] Python >=3.10 not found. Install Python or set AIDLC_PYTHON to its executable path.')
exit 1
