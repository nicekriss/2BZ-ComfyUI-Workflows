param([string]$ComfyURL)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    if (-not $ComfyURL) { $ComfyURL = Read-Host 'Enter the URL of YOUR running ComfyUI (example http://127.0.0.1:8188)' }
    $uri = [Uri]$ComfyURL
    if (-not $uri.IsLoopback -or $uri.Scheme -notin @('http','https')) { throw 'Only your local ComfyUI URL is allowed.' }
    $base = $uri.GetLeftPart([System.UriPartial]::Authority)
    $stats = Invoke-RestMethod -Uri "$base/system_stats" -TimeoutSec 15
    $info = Invoke-RestMethod -Uri "$base/object_info" -TimeoutSec 30
    $graph = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot '2BZ_FastH3_USDU.json') | ConvertFrom-Json
    $errorsFound = 0
    Write-Host "Connected backend: $base"
    Write-Host ('ComfyUI: ' + $stats.system.comfyui_version)
    foreach ($type in @($graph.nodes.type | Sort-Object -Unique)) {
        if ($type -eq 'MarkdownNote') { continue }
        if ($info.PSObject.Properties.Name -notcontains $type) {
            Write-Host "MISSING NODE: $type" -ForegroundColor Red
            $errorsFound++
        }
    }
    $models = @(
        @('UNETLoader', 'unet_name', 'minimax_h3_fastvideo_vsa_datafree_1300step_4step_int8_convrot.safetensors'),
        @('CLIPLoader', 'clip_name', 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'),
        @('VAELoader', 'vae_name', 'minimax_h3_video_vae_fp16.safetensors'),
        @('UpscaleModelLoader', 'model_name', 'RealESRGAN_x2plus.pth')
    )
    foreach ($model in $models) {
        $type, $field, $name = $model
        if ($info.PSObject.Properties.Name -notcontains $type) { continue }
        $choices = @($info.$type.input.required.$field[0])
        if ($choices -contains $name) {
            Write-Host "MODEL LISTED: $name" -ForegroundColor Green
        } else {
            Write-Host "MODEL NOT AT EXPECTED PATH: $name" -ForegroundColor Red
            Write-Host 'If placed in a subfolder, select its actual path in the loader and verify manually.'
            $errorsFound++
        }
    }
    if ($errorsFound) { throw "$errorsFound readiness issue(s). See START-HERE-ko.md stage 4." }
    Write-Host 'SERVER READY: workflow node types and all four model names are listed.' -ForegroundColor Green
    Write-Host 'This does NOT verify model file integrity, loaded VSA gates, the active canvas, or rendering.'
    Write-Host 'In ComfyUI: open the bundled JSON, select YOUR input video, check all loaders, and run a short clip.'
    exit 0
} catch {
    Write-Host ('NOT READY: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
