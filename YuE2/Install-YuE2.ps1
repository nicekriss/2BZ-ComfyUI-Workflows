param([string]$ComfyUIRoot, [string]$PythonExe, [string]$ModelsRoot, [switch]$CheckOnly)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Windows.Forms
    if (-not $ComfyUIRoot) {
        $picker = New-Object System.Windows.Forms.FolderBrowserDialog
        $picker.Description = 'Select ComfyUI (main.py), or its portable parent folder'
        if ($picker.ShowDialog() -ne 'OK') { throw 'Cancelled.' }
        $ComfyUIRoot = $picker.SelectedPath
    }
    $root = (Resolve-Path -LiteralPath $ComfyUIRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $root 'main.py'))) { $root = Join-Path $root 'ComfyUI' }
    if (-not (Test-Path -LiteralPath (Join-Path $root 'main.py'))) { throw 'Cannot find main.py. Select the actual ComfyUI folder, not the Desktop app folder.' }
    if (-not $PythonExe) {
        $candidates = @((Join-Path $root '.venv\Scripts\python.exe'), (Join-Path $root 'venv\Scripts\python.exe'),
            (Join-Path (Split-Path $root -Parent) 'python_embeded\python.exe'),
            (Join-Path (Split-Path $root -Parent) 'python_embedded\python.exe'))
        $found = @($candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -Unique)
        if ($found.Count -eq 1) { $PythonExe = $found[0] } else {
            $picker = New-Object System.Windows.Forms.OpenFileDialog
            $picker.Title = 'Select the python.exe used by this ComfyUI'
            $picker.Filter = 'Python (python.exe)|python.exe'
            $picker.InitialDirectory = $root
            if ($picker.ShowDialog() -ne 'OK') { throw 'Cancelled.' }
            $PythonExe = $picker.FileName
        }
    }
    $PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
    $extra = @()
    if ($CheckOnly) { $extra += '--check-only' } else {
        if (-not $ModelsRoot) {
            $picker = New-Object System.Windows.Forms.FolderBrowserDialog
            $picker.Description = 'Select models folder (existing shared models folder is also OK)'
            $picker.SelectedPath = Join-Path $root 'models'
            if ($picker.ShowDialog() -ne 'OK') { throw 'Cancelled.' }
            $ModelsRoot = $picker.SelectedPath
        }
        $extra += @('--models', $ModelsRoot)
        Write-Host "ComfyUI: $root`nPython: $PythonExe`nModels: $ModelsRoot"
    }
    $env:PYTHONUTF8 = '1'
    & $PythonExe -X utf8 (Join-Path $PSScriptRoot 'install_yue2.py') --root $root @extra
    exit $LASTEXITCODE
} catch {
    Write-Host ('FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
