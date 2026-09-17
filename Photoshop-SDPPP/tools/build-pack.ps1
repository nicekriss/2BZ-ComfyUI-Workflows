# 작업팩 만들기: 정리가 끝난 워크플로우를 ComfyUI에서 가져와 설치기 workflows\ 로 넣는다.
# - 설치기 manifest에 없는 모델·노드를 쓰면 경고한다(구독자 PC에서 MISSING 방지)
# - 테스트 입력 이미지·개인 흔적(에이전트 메타데이터)을 지운다
param(
    [Parameter(Mandatory)] [string[]]$Workflow,           # 워크플로우 json 경로(여러 개 가능)
    [string]$Server = 'http://127.0.0.1:8188',            # 노드 소속 확인용
    [string]$ManifestPath,
    [string]$OutDir
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ManifestPath) { $ManifestPath = Join-Path $here '..\manifest.json' }
if (-not $OutDir) { $OutDir = Join-Path $here '..\workflows' }
$manifest = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Force $OutDir | Out-Null

$modelNames = @{}
foreach ($m in $manifest.models) {
    $sub = ($m.folder -split '/', 2)[1]
    $key = if ($sub) { "$($sub -replace '/', '\')\$($m.file)" } else { $m.file }
    $modelNames[$key.ToLower()] = $true
}
$map = @{}
$manifest.workflow_name_map.PSObject.Properties | ForEach-Object { $map[$_.Name] = $_.Value }
$providedNodes = @{}
$manifest.custom_nodes | ForEach-Object { foreach ($p in $_.provides) { $providedNodes[$p] = $_.folder } }

$objectInfo = $null
try { $objectInfo = Invoke-RestMethod "$Server/object_info" -TimeoutSec 60 } catch { Write-Host "  [주의] $Server 에 연결하지 못해 노드 소속 검사는 건너뜁니다." -ForegroundColor Yellow }

$problems = 0
foreach ($wfPath in $Workflow) {
    $raw = Get-Content $wfPath -Raw -Encoding UTF8
    foreach ($k in $map.Keys) { $raw = $raw.Replace(($k -replace '\\', '\\'), ($map[$k] -replace '\\', '\\')) }
    $wf = $raw | ConvertFrom-Json
    $name = [IO.Path]::GetFileName($wfPath)
    Write-Host "━━ $name ($($wf.nodes.Count) 노드)" -ForegroundColor Cyan

    foreach ($n in $wf.nodes) {
        # 모델 파일 이름 검사
        foreach ($v in @($n.widgets_values)) {
            if ($v -is [string] -and $v -match '\.(safetensors|ckpt|pt|pth|gguf|bin)$') {
                $mapped = if ($map.ContainsKey($v)) { $map[$v] } else { $v }
                if (-not $modelNames.ContainsKey($mapped.ToLower())) {
                    Write-Host "  [누락] 노드 $($n.id) $($n.type): 모델 '$mapped' 가 manifest에 없습니다." -ForegroundColor Red
                    $problems++
                }
            }
        }
        # 테스트 입력 이미지 → ComfyUI 기본 example.png (SD-PPP가 실행 시 Photoshop 이미지로 교체)
        if ($n.type -eq 'LoadImage' -and $n.widgets_values[0] -ne 'example.png') {
            Write-Host "  [정리] 노드 $($n.id) 입력 '$($n.widgets_values[0])' → example.png"
            $n.widgets_values[0] = 'example.png'
            if ($n.widgets_values_named) { $n.widgets_values_named.image = 'example.png' }
        }
        # 커스텀 노드 소속 검사
        if ($objectInfo) {
            $info = $objectInfo.($n.type)
            if (-not $info) {
                if ($n.type -notin 'MarkdownNote', 'Note', 'Reroute', 'PrimitiveNode') {
                    Write-Host "  [주의] $($n.type): 서버에 없는 노드입니다." -ForegroundColor Yellow
                }
            } elseif ($info.python_module -like 'custom_nodes.*' -and -not $providedNodes.ContainsKey($n.type)) {
                Write-Host "  [누락] $($n.type) ($($info.python_module)) 가 manifest 노드 목록에 없습니다." -ForegroundColor Red
                $problems++
            }
        }
    }
    $saves = @($wf.nodes | Where-Object { $_.type -eq 'SaveImage' -and $_.mode -eq 0 })
    if ($saves.Count -gt 1) { Write-Host "  [주의] 켜진 저장 노드 $($saves.Count)개 — 기본 실행이 여러 결과를 만듭니다." -ForegroundColor Yellow }
    if ($wf.extra.PSObject.Properties['comfyui_mcp']) { $wf.extra.PSObject.Properties.Remove('comfyui_mcp') }

    $out = Join-Path $OutDir $name
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($out, ($wf | ConvertTo-Json -Depth 100 -Compress), $utf8)
    Write-Host "  → $out" -ForegroundColor Green
}
if ($problems) { Write-Host "문제 $problems 건: manifest.json 에 모델/노드를 추가하거나 워크플로우를 고친 뒤 다시 실행하세요." -ForegroundColor Red; exit 1 }
