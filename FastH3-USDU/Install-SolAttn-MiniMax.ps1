param([string]$ComfyUIRoot, [string]$PythonExe, [switch]$CheckOnly, [switch]$Restore, [switch]$InstallUSDU)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    if (([int]$CheckOnly.IsPresent + [int]$Restore.IsPresent + [int]$InstallUSDU.IsPresent) -gt 1) { throw 'Choose one operation only.' }
    Add-Type -AssemblyName System.Windows.Forms
    if (-not $ComfyUIRoot) {
        $picker = New-Object System.Windows.Forms.FolderBrowserDialog
        $picker.Description = 'Select ComfyUI (main.py), or the portable folder containing ComfyUI'
        if ($picker.ShowDialog() -ne 'OK') { throw 'Cancelled.' }
        $ComfyUIRoot = $picker.SelectedPath
    }
    $root = (Resolve-Path -LiteralPath $ComfyUIRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $root 'main.py'))) {
        $root = Join-Path $root 'ComfyUI'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $root 'main.py'))) { throw 'Cannot find ComfyUI main.py.' }
    $root = (Resolve-Path -LiteralPath $root).Path
    if (-not $PythonExe) {
        $candidates = @(
            (Join-Path $root '.venv\Scripts\python.exe'),
            (Join-Path $root 'venv\Scripts\python.exe'),
            (Join-Path (Split-Path $root -Parent) 'python_embeded\python.exe'),
            (Join-Path $root 'python_embeded\python.exe'),
            (Join-Path (Split-Path $root -Parent) 'python_embedded\python.exe')
        )
        $found = @($candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -Unique)
        if ($found.Count -eq 1) {
            $PythonExe = $found[0]
        } else {
            $picker = New-Object System.Windows.Forms.OpenFileDialog
            $picker.Title = 'Select the python.exe used by this ComfyUI'
            $picker.Filter = 'Python (python.exe)|python.exe'
            $picker.InitialDirectory = $root
            if ($picker.ShowDialog() -ne 'OK') { throw 'Python selection cancelled.' }
            $PythonExe = $picker.FileName
        }
    }
    $PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
    if (-not $CheckOnly) {
        $running = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
            Where-Object { $_.CommandLine -and $_.CommandLine -match 'main\.py' -and
                ($_.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                 $_.CommandLine.IndexOf($PythonExe, [StringComparison]::OrdinalIgnoreCase) -ge 0) })
        if ($running.Count) { throw 'This ComfyUI is still running. Stop it in Comfy Desktop, then retry.' }
        $message = @("ComfyUI: $root", "Python: $PythonExe", '', 'Confirm this is the intended environment and ComfyUI is stopped.', 'Install: SolAttn v5, Kitchen 0.2.32 if needed, and the fingerprint-verified H3 gate patch in TWO core files. Backups are retained. Unknown core versions are refused. Torch is not updated.', 'Restore: restore backed-up H3 and Kitchen files; preserve files changed since installation.', 'USDU and models are separate steps. See START-HERE-ko.md.') -join [Environment]::NewLine
        if ($InstallUSDU) {
            $message = @("ComfyUI: $root", '', 'Install the tested H3 USDU fork and its pinned submodule from GitHub. Git for Windows is required.', 'Existing installations are checked, never overwritten. No pip or model downloads. ComfyUI must be stopped.') -join [Environment]::NewLine
        }
        $answer = [System.Windows.Forms.MessageBox]::Show($message, '2BZ setup', 'OKCancel', 'Information')
        if ($answer -ne 'OK') { throw 'Cancelled; no changes.' }
    }
    $extra = @()
    if ($InstallUSDU) {
        & $PythonExe -s (Join-Path $PSScriptRoot 'install_usdu.py') --root $root
        exit $LASTEXITCODE
    }
    if ($CheckOnly) { $extra += '--check-only' }
    if ($Restore) { $extra += '--restore' }
    & $PythonExe -s (Join-Path $PSScriptRoot 'install_solattn.py') --root $root @extra
    exit $LASTEXITCODE
} catch {
    Write-Host ('FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
