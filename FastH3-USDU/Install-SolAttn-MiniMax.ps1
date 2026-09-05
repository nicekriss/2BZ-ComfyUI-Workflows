param([string]$ComfyUIRoot, [string]$PythonExe, [switch]$CheckOnly)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$download = $null
try {
    if (-not $ComfyUIRoot) {
        $shell = New-Object -ComObject Shell.Application
        $picked = $shell.BrowseForFolder(0, 'Select ComfyUI folder containing main.py and custom_nodes', 0)
        if ($null -eq $picked) { throw 'Folder selection cancelled.' }
        $ComfyUIRoot = $picked.Self.Path
    }
    $root = (Resolve-Path -LiteralPath $ComfyUIRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $root 'main.py'))) { throw 'main.py not found in selected folder.' }
    if (-not $PythonExe) {
        $candidates = @(
            (Join-Path $root '.venv\Scripts\python.exe'),
            (Join-Path $root 'venv\Scripts\python.exe'),
            (Join-Path (Split-Path $root -Parent) 'python_embeded\python.exe'),
            (Join-Path $root 'python_embeded\python.exe')
        )
        $found = @($candidates | Where-Object { Test-Path -LiteralPath $_ })
        if ($found.Count -ne 1) { throw 'Cannot identify one Python environment. Run with -PythonExe pointing to the Python used by ComfyUI.' }
        $PythonExe = $found[0]
    }
    $PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
    Push-Location -LiteralPath $root
    try {
        & $PythonExe (Join-Path $PSScriptRoot 'check_solattn.py')
        if ($LASTEXITCODE -ne 0) { throw 'VSA preflight failed. Follow README update guidance; no packages or nodes have been changed.' }
    } finally { Pop-Location }
    if ($CheckOnly) { Write-Host 'Preflight passed; no files changed.'; exit 0 }

    $nodeDir = Join-Path $root 'custom_nodes\ComfyUI-SolAttn-MiniMax'
    $nodeFile = Join-Path $nodeDir '__init__.py'
    $expected = '97C9D56FDC7C9A102E59BFF9AC8D79503299514D061892088A03D99DCF415B0C'
    if (Test-Path -LiteralPath $nodeFile) {
        if ((Get-FileHash -LiteralPath $nodeFile -Algorithm SHA256).Hash -ne $expected) {
            throw 'An existing different SolAttn node was found. It was preserved; review it manually before replacing it.'
        }
        Write-Host 'Verified v5 node is already installed. No files changed.'
        exit 0
    }
    $download = Join-Path ([IO.Path]::GetTempPath()) ('solattn-' + [guid]::NewGuid().ToString() + '.py')
    Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/user-attachments/files/31576773/sol_attn_minimax_v5.py' -OutFile $download
    if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash -ne $expected) { throw 'Original v5 file SHA-256 mismatch. Installation stopped.' }
    New-Item -ItemType Directory -Path $nodeDir -Force | Out-Null
    Copy-Item -LiteralPath $download -Destination $nodeFile
    Write-Host 'Node installed. Restart ComfyUI. Select VSA (FastVideo); check the render log for VSA tiles and fallback errors.'
    Write-Host 'Preflight checks capabilities, not full-model output or speed.'
} catch {
    Write-Host ('FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if ($download -and (Test-Path -LiteralPath $download)) { Remove-Item -LiteralPath $download }
}
