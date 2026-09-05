param([string]$ComfyUIRoot, [string]$PythonExe, [switch]$CheckOnly, [switch]$Restore)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
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
        $message = @("ComfyUI: $root", "Python: $PythonExe", '', 'Confirm this is the intended environment and ComfyUI is stopped.', 'Only comfy-kitchen may be changed to 0.2.32; existing files will be backed up. Torch is not updated.') -join [Environment]::NewLine
        $answer = [System.Windows.Forms.MessageBox]::Show($message, '2BZ SolAttn installer', 'OKCancel', 'Information')
        if ($answer -ne 'OK') { throw 'Cancelled; no changes.' }
    }
    $extra = @()
    if ($CheckOnly) { $extra += '--check-only' }
    if ($Restore) { $extra += '--restore' }
    & $PythonExe -s (Join-Path $PSScriptRoot 'install_solattn.py') --root $root @extra
    exit $LASTEXITCODE
} catch {
    Write-Host ('FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
