param(
    [string]$ComfyUIRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-ComfyUIRoot {
    param([string]$StartPath)

    $current = [System.IO.DirectoryInfo](Resolve-Path -LiteralPath $StartPath)
    while ($null -ne $current) {
        if ((Test-Path -LiteralPath (Join-Path $current.FullName "main.py")) -and
            (Test-Path -LiteralPath (Join-Path $current.FullName "custom_nodes"))) {
            return $current.FullName
        }
        $current = $current.Parent
    }
    return $null
}

try {
    if ($ComfyUIRoot) {
        $root = (Resolve-Path -LiteralPath $ComfyUIRoot).Path
    } else {
        $root = Find-ComfyUIRoot -StartPath $PSScriptRoot
    }

    if (-not $root) {
        $shell = New-Object -ComObject Shell.Application
        $picked = $shell.BrowseForFolder(0, "Select your ComfyUI folder (the folder containing main.py)", 0)
        if ($null -eq $picked) {
            throw "Installation cancelled."
        }
        $root = $picked.Self.Path
    }

    if (-not (Test-Path -LiteralPath (Join-Path $root "main.py"))) {
        throw "The selected folder is not a ComfyUI folder: $root"
    }

    $nodeDir = Join-Path $root "custom_nodes\ComfyUI-SolAttn-MiniMax"
    $nodeFile = Join-Path $nodeDir "__init__.py"
    $download = Join-Path $env:TEMP ("sol_attn_minimax_v5_{0}.py" -f $PID)
    $sourceUrl = "https://github.com/user-attachments/files/31576773/sol_attn_minimax_v5.py"

    Write-Host "Downloading the original Sol-Attn MiniMax node from kijai's Comfy-Kitchen PR..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $sourceUrl -OutFile $download -UseBasicParsing
    if (-not (Select-String -LiteralPath $download -Pattern "SolAttnMiniMax" -Quiet)) {
        throw "The downloaded file did not pass the node-content check."
    }

    New-Item -ItemType Directory -Path $nodeDir -Force | Out-Null
    if (Test-Path -LiteralPath $nodeFile) {
        $installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $nodeFile).Hash
        $downloadHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $download).Hash
        if ($installedHash -ne $downloadHash) {
            $backup = Join-Path $nodeDir ("__init__.backup-{0}.py" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
            Copy-Item -LiteralPath $nodeFile -Destination $backup
            Write-Host "Existing node backed up: $backup" -ForegroundColor Yellow
        }
    }
    Copy-Item -LiteralPath $download -Destination $nodeFile -Force
    Remove-Item -LiteralPath $download -Force
    Write-Host "Installed: $nodeFile" -ForegroundColor Green

    $parent = Split-Path -Parent $root
    $pythonCandidates = @(
        (Join-Path $root ".venv\Scripts\python.exe"),
        (Join-Path $root "venv\Scripts\python.exe"),
        (Join-Path $parent "python_embeded\python.exe"),
        (Join-Path $root "python_embeded\python.exe")
    )
    $python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

    if ($python) {
        & $python -c "from comfy_kitchen import sol_attn" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Updating comfy-kitchen for the required Sol-Attn CUDA kernel..." -ForegroundColor Cyan
            & $python -m pip install --upgrade "comfy-kitchen>=0.2.32"
            if ($LASTEXITCODE -ne 0) {
                throw "comfy-kitchen could not be updated. Update ComfyUI, then run this installer again."
            }
        }

        & $python -c "from comfy_kitchen import sol_attn" 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "The Sol-Attn kernel is still unavailable. Update ComfyUI, then run this installer again."
        }
        Write-Host "comfy-kitchen Sol-Attn kernel: OK" -ForegroundColor Green
    } else {
        Write-Host "ComfyUI's Python was not found, so the kernel could not be checked." -ForegroundColor Yellow
        Write-Host "Update ComfyUI before starting it. comfy-kitchen v0.2.32 or newer is required." -ForegroundColor Yellow
    }

    Write-Host "Installation complete. Fully restart ComfyUI and search for: Patch Sol-Attn (MiniMax)" -ForegroundColor Green
    Write-Host "Source: https://github.com/Comfy-Org/comfy-kitchen/pull/117"
} catch {
    Write-Host "Installation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
