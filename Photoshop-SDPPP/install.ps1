# 베짱이 Photoshop AI 설치 도우미 v0.1
# 순서: 내 PC 확인 → 설치 준비 → 노드·모델 설치 → Photoshop 플러그인 → 연결 확인
param(
    [string]$ComfyPath,          # ComfyUI 폴더(main.py가 있는 곳)를 직접 지정
    [string]$ModelsPath,         # 모델 폴더를 직접 지정
    [switch]$CheckOnly          # 점검만 하고 아무것도 바꾸지 않음
)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Manifest = Get-Content (Join-Path $Root 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$StateFile = Join-Path $Root 'state\install-state.json'

function Step($n, $title) { Write-Host ''; Write-Host "━━ $n. $title" -ForegroundColor Cyan }
function Ok($m) { Write-Host "  [확인] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  [주의] $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "  [실패] $m" -ForegroundColor Red }
function Info($m) { Write-Host "  $m" }
function Ask($m) { $a = Read-Host "  $m [Y/n]"; return ($a -eq '' -or $a -match '^[yY]') }

function Save-State($key, $value) {
    $dir = Split-Path $StateFile
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
    $s = @{}
    if (Test-Path $StateFile) {
        (Get-Content $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $s[$_.Name] = $_.Value }
    }
    $s[$key] = $value
    $s['updated_at'] = (Get-Date).ToString('s')
    $s | ConvertTo-Json -Depth 5 | Out-File $StateFile -Encoding utf8
}

Write-Host ''
Write-Host '  포토샵에서 그리고, AI로 완성하세요.' -ForegroundColor White
Write-Host "  $($Manifest.name) 설치 도우미 $($Manifest.release)" -ForegroundColor DarkGray

# ─────────────────────────────────────────────
Step 1 '내 PC 확인'

$gpuOk = $false
$smi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
if ($smi) {
    $gpus = & $smi.Source --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
    foreach ($g in $gpus) {
        $p = $g -split ',\s*'
        $totalGb = [math]::Round([int]$p[1] / 1024, 1)
        $freeGb = [math]::Round(([int]$p[1] - [int]$p[2]) / 1024, 1)
        Ok "GPU: $($p[0]) · 전용 메모리 ${totalGb}GB (지금 여유 ${freeGb}GB)"
        if ($totalGb -lt 12) { Warn '12GB 미만 GPU는 아직 검증 전입니다. 첫 테스트는 작은 크기로 진행하세요.' }
        $gpuOk = $true
    }
} else {
    Fail 'NVIDIA GPU(드라이버)를 찾지 못했습니다. 이 버전은 Windows + NVIDIA 전용입니다.'
}

$ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
if ($ramGb -lt 16) { Warn "RAM ${ramGb}GB — 16GB 이상을 권장합니다." } else { Ok "RAM ${ramGb}GB" }

$psExe = $null
$psCandidates = @(Get-ChildItem "$env:ProgramFiles\Adobe" -Directory -Filter 'Adobe Photoshop*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
foreach ($c in $psCandidates) {
    $exe = Join-Path $c.FullName 'Photoshop.exe'
    if (Test-Path $exe) { $psExe = $exe; break }
}
if ($psExe) {
    $psVer = (Get-Item $psExe).VersionInfo.ProductVersion
    if ([version]($psVer -replace '[^\d\.].*$', '') -ge [version]$Manifest.verified.photoshop_min) { Ok "Photoshop 발견: $psVer" }
    else { Warn "Photoshop $psVer — $($Manifest.verified.photoshop_min) 이상이 필요합니다." }
} else {
    Warn 'Photoshop을 찾지 못했습니다. Creative Cloud에서 Photoshop을 설치한 뒤 다시 실행하세요. (ComfyUI 쪽 설치는 먼저 진행할 수 있습니다.)'
}

# ComfyUI 후보: Comfy Desktop 설치 목록 → 구버전 Desktop 설정 → 포터블 흔한 위치
function Get-ComfyCandidates {
    $list = @()
    foreach ($cfg in @("$env:APPDATA\Comfy Desktop\installations.json")) {
        if (Test-Path $cfg) {
            foreach ($i in (Get-Content $cfg -Raw -Encoding UTF8 | ConvertFrom-Json)) {
                if ($i.installPath -and (Test-Path (Join-Path $i.installPath 'ComfyUI\main.py'))) {
                    $list += [pscustomobject]@{ Name = "Comfy Desktop · $($i.name)"; Path = (Join-Path $i.installPath 'ComfyUI'); Id = $i.id }
                }
            }
        }
    }
    $legacy = "$env:APPDATA\ComfyUI\config.json"
    if (Test-Path $legacy) {
        $b = (Get-Content $legacy -Raw -Encoding UTF8 | ConvertFrom-Json).basePath
        if ($b -and (Test-Path (Join-Path $b 'ComfyUI\main.py'))) { $list += [pscustomobject]@{ Name = 'ComfyUI Desktop'; Path = (Join-Path $b 'ComfyUI'); Id = $null } }
    }
    foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free -gt 0 })) {
        foreach ($rel in 'ComfyUI_windows_portable\ComfyUI', 'ComfyUI') {
            $p = Join-Path $drive.Root $rel
            if (Test-Path (Join-Path $p 'main.py')) { $list += [pscustomobject]@{ Name = 'ComfyUI'; Path = $p; Id = $null } }
        }
    }
    $list | Sort-Object Path -Unique
}

if (-not $ComfyPath) {
    $cands = @(Get-ComfyCandidates)
    if ($cands.Count -eq 0) {
        Fail 'ComfyUI를 찾지 못했습니다.'
        Info '공식 ComfyUI Desktop을 설치하고 한 번 실행한 뒤 이 설치 도우미를 다시 실행하세요: https://www.comfy.org/download'
        Info '다른 위치에 있다면: .\install.ps1 -ComfyPath "D:\...\ComfyUI"'
        exit 1
    }
    Info '연결할 ComfyUI를 고르세요:'
    for ($k = 0; $k -lt $cands.Count; $k++) { Info "  [$($k + 1)] $($cands[$k].Name) — $($cands[$k].Path)" }
    $pick = if ($cands.Count -eq 1) { 1 } else { [int](Read-Host '  번호') }
    $Comfy = $cands[$pick - 1]
    $ComfyPath = $Comfy.Path
} else {
    if (-not (Test-Path (Join-Path $ComfyPath 'main.py'))) { Fail "main.py가 없습니다: $ComfyPath"; exit 1 }
    $ComfyPath = (Resolve-Path $ComfyPath).Path.TrimEnd('\')
    $Comfy = Get-ComfyCandidates | Where-Object { $_.Path -ieq $ComfyPath } | Select-Object -First 1
    if (-not $Comfy) { $Comfy = [pscustomobject]@{ Name = '직접 지정'; Path = $ComfyPath; Id = $null } }
}
Ok "ComfyUI: $ComfyPath"

$Python = @(
    (Join-Path $ComfyPath '.venv\Scripts\python.exe'),
    (Join-Path (Split-Path $ComfyPath) '.venv\Scripts\python.exe'),
    (Join-Path (Split-Path $ComfyPath) 'python_embeded\python.exe')
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($Python) { Ok "Python: $Python" } else { Warn 'ComfyUI 전용 Python을 찾지 못했습니다. 노드 의존성 설치는 건너뜁니다.' }

# 모델 폴더: Desktop이 공유 모델 경로를 쓰면 그 base_path, 아니면 ComfyUI\models
if (-not $ModelsPath) {
    $ModelsPath = Join-Path $ComfyPath 'models'
    if ($Comfy.Id) {
        $yaml = "$env:APPDATA\Comfy Desktop\instance-model-paths\$($Comfy.Id).yaml"
        if (Test-Path $yaml) {
            $m = Select-String -Path $yaml -Pattern "^\s+base_path:\s*'?([^'\r\n]+)'?" | Select-Object -First 1
            if ($m) { $ModelsPath = $m.Matches[0].Groups[1].Value.Trim() }
        }
    }
    $KnownModelsPath = $ModelsPath   # ComfyUI가 이미 알고 있는 폴더

    # SSD가 좁으면 다른 드라이브(HDD)에 둘 수 있게 물어본다. 점검 모드에서는 묻지 않는다.
    if (-not $CheckOnly) {
        $needAll = [math]::Round((($Manifest.models | Measure-Object -Property size -Sum).Sum) / 1GB, 1)
        Info ''
        Info "모델 파일(약 ${needAll}GB)을 어디에 저장할까요?"
        $fixed = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Sort-Object DeviceID)
        foreach ($d in $fixed) {
            $mark = if ($ModelsPath.StartsWith($d.DeviceID, [StringComparison]::OrdinalIgnoreCase)) { ' ← 기본' } else { '' }
            Info ("    {0}  여유 {1,6:N0}GB / 전체 {2,6:N0}GB{3}" -f $d.DeviceID, ($d.FreeSpace / 1GB), ($d.Size / 1GB), $mark)
        }
        Info "  그냥 Enter = 기본 위치 ($ModelsPath)"
        Info '  다른 드라이브에 두려면 드라이브 문자만 입력 (예: D)'
        $ans = (Read-Host '  선택').Trim().TrimEnd(':', '\')
        if ($ans -match '^[a-zA-Z]$') {
            if ($fixed.DeviceID -contains "$($ans.ToUpper()):") { $ModelsPath = "$($ans.ToUpper()):\AI_Models" }
            else { Warn "$($ans.ToUpper()): 드라이브를 찾지 못해 기본 위치를 사용합니다." }
        } elseif ($ans -match '^[a-zA-Z]:\\') {
            $ModelsPath = $ans
        }
    }
} else {
    $KnownModelsPath = $null
}
# ComfyUI가 모르는 폴더면 나중에 extra_model_paths.yaml로 등록해야 한다
$RegisterModelsPath = ($ModelsPath -ne $KnownModelsPath) -and ($ModelsPath -ne (Join-Path $ComfyPath 'models'))
Ok "모델 폴더: $ModelsPath$(if ($RegisterModelsPath) { '  (ComfyUI에 자동 등록합니다)' })"

$needBytes = ($Manifest.models | ForEach-Object {
    $dest = Join-Path $ModelsPath (Join-Path $_.folder $_.file)
    if (Test-Path $dest) { 0 } else { [int64]$_.size }
} | Measure-Object -Sum).Sum
$drive = Get-PSDrive -Name ($ModelsPath.Substring(0, 1))
$freeGb = [math]::Round($drive.Free / 1GB, 1)
$needGb = [math]::Round($needBytes / 1GB, 1)
if ($drive.Free -lt ($needBytes + 2GB)) { Fail "디스크 공간 부족: 필요 약 ${needGb}GB + 여유 2GB, 현재 ${freeGb}GB"; if (-not $CheckOnly) { exit 1 } }
else { Ok "새로 받을 모델 ${needGb}GB · 드라이브 여유 ${freeGb}GB" }

if ($CheckOnly) { Write-Host ''; Info '점검만 수행했습니다. 아무것도 바꾸지 않았습니다.'; exit 0 }
if (-not $gpuOk -and -not (Ask 'NVIDIA GPU가 확인되지 않았습니다. 그래도 계속할까요?')) { exit 1 }

# ─────────────────────────────────────────────
Step 2 '설치 준비'
$nodes = @($Manifest.custom_nodes)
Info '설치할 구성:'
$nodes | ForEach-Object { Info "  · 노드 $($_.folder) ($($_.repo) @ $($_.commit.Substring(0,7)), $($_.license))" }
$Manifest.models | ForEach-Object { Info "  · 모델 $($_.role): $($_.file) ($([math]::Round($_.size/1GB,2))GB) — $($_.source)" }
Info "  · Photoshop 플러그인 SD-PPP $($Manifest.plugin.version) + 입력창 포커스 패치"
Info '  · 모델 이용 조건은 위 출처 페이지에서 확인하세요.'
if (-not (Ask '이 구성으로 설치할까요?')) { exit 0 }

$Temp = Join-Path $Root 'downloads'
New-Item -ItemType Directory -Force $Temp | Out-Null

# 실행 중이면 새 노드·플러그인이 반영되지 않는다. 강제로 끄지 않고 사용자가 닫게 한다.
while ($true) {
    $busy = @()
    if (Get-Process 'ComfyUI' -ErrorAction SilentlyContinue) { $busy += 'ComfyUI' }
    foreach ($port in 8188, 8000) {
        try { Invoke-RestMethod "http://127.0.0.1:$port/system_stats" -TimeoutSec 2 | Out-Null; $busy += "ComfyUI 서버(:$port)" } catch {}
    }
    if (Get-Process 'Photoshop' -ErrorAction SilentlyContinue) { $busy += 'Photoshop' }
    if (-not $busy) { Ok '실행 중인 ComfyUI/Photoshop 없음'; break }
    Warn "실행 중: $($busy -join ', ')"
    Info '작업을 저장하고 두 프로그램을 닫아주세요. 설치 후에 다시 켜서 테스트합니다.'
    if (-not (Ask '닫았으면 계속할까요? (아니오를 누르면 중단)')) { exit 0 }
}

function Get-File($url, $dest, $expectedSize) {
    # curl.exe 이어받기(-C -). 실패하면 한 번 더 시도.
    $part = "$dest.part"
    for ($try = 1; $try -le 2; $try++) {
        & curl.exe -L --fail --retry 3 --retry-delay 3 -C - -o $part $url
        if ($LASTEXITCODE -eq 0 -and (-not $expectedSize -or (Get-Item $part).Length -eq $expectedSize)) { break }
        if ($LASTEXITCODE -eq 33 -and (Test-Path $part)) { Remove-Item $part -Force }  # 서버가 이어받기 미지원
    }
    if (-not (Test-Path $part)) { throw "다운로드 실패: $url" }
    return $part
}

# ─────────────────────────────────────────────
Step 3 'ComfyUI 노드 설치'
$customNodes = Join-Path $ComfyPath 'custom_nodes'
foreach ($n in $nodes) {
    $target = Join-Path $customNodes $n.folder
    $existing = Get-ChildItem $customNodes -Directory | Where-Object { $_.Name -ieq $n.folder -or $_.Name -ieq ($n.repo -split '/')[1] } | Select-Object -First 1
    if ($existing) {
        $head = git -C $existing.FullName rev-parse HEAD 2>$null
        if ($head -eq $n.commit) { Ok "$($n.folder): 검증된 버전이 이미 있습니다." }
        else { Warn "$($existing.Name): 이미 설치됨(다른 버전일 수 있음). 덮어쓰지 않고 그대로 사용합니다." }
        continue
    }
    Info "$($n.folder) 받는 중..."
    $zip = Get-File "https://github.com/$($n.repo)/archive/$($n.commit).zip" (Join-Path $Temp "$($n.id).zip") $null
    $ex = Join-Path $Temp "$($n.id)_x"
    if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }
    Expand-Archive $zip $ex -Force
    Move-Item (Get-ChildItem $ex -Directory | Select-Object -First 1).FullName $target
    if ($n.requirements -and $Python -and (Test-Path (Join-Path $target 'requirements.txt'))) {
        & $Python -m pip install -r (Join-Path $target 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { Warn "$($n.folder) 의존성 설치에 실패했습니다. ComfyUI Manager에서 다시 시도하세요." }
    }
    Ok "$($n.folder) 설치"
}
Save-State 'nodes' 'done'

# ─────────────────────────────────────────────
Step 4 '모델 준비'
if ($RegisterModelsPath) {
    # main.py 옆의 extra_model_paths.yaml은 ComfyUI가 시작할 때 자동으로 읽는다.
    New-Item -ItemType Directory -Force $ModelsPath | Out-Null
    $extra = Join-Path $ComfyPath 'extra_model_paths.yaml'
    $existing = if (Test-Path $extra) { [IO.File]::ReadAllText($extra) } else { '' }
    if ($existing -match [regex]::Escape($ModelsPath)) {
        Ok "ComfyUI에 이미 등록된 폴더입니다: $ModelsPath"
    } else {
        $key = 'psai_models'
        if ($existing -match "(?m)^$key\s*:") { $key = "psai_models_$(Get-Date -Format yyyyMMddHHmmss)" }
        $block = @(
            "$key`:",
            "  base_path: '$ModelsPath'",
            "  checkpoints: checkpoints/",
            "  controlnet: controlnet/",
            "  loras: loras/",
            "  vae: vae/",
            "  upscale_models: upscale_models/",
            ''
        ) -join "`n"
        if ($existing -and -not $existing.EndsWith("`n")) { $existing += "`n" }
        if ($existing) { Copy-Item $extra "$extra.bak-$(Get-Date -Format yyyyMMddHHmmss)" }
        [IO.File]::WriteAllText($extra, $existing + $block, (New-Object System.Text.UTF8Encoding($false)))
        Ok "ComfyUI에 모델 폴더 등록: $ModelsPath"
    }
    Save-State 'models_path' $ModelsPath
}
foreach ($m in $Manifest.models) {
    $dir = Join-Path $ModelsPath ($m.folder -replace '/', '\')
    $dest = Join-Path $dir $m.file
    New-Item -ItemType Directory -Force $dir | Out-Null
    if ((Test-Path $dest) -and (Get-Item $dest).Length -eq $m.size) {
        Info "$($m.file) 확인 중(해시)..."
        if ((Get-FileHash $dest -Algorithm SHA256).Hash -eq $m.sha256) { Ok "$($m.file): 이미 있음" ; continue }
        Warn "$($m.file): 같은 이름이지만 내용이 다릅니다. 기존 파일은 두고 새로 받지 않습니다 — 확인 후 직접 교체하세요."
        continue
    }
    Info "$($m.role) 받는 중: $($m.file)"
    $part = Get-File $m.url $dest $m.size
    if ((Get-FileHash $part -Algorithm SHA256).Hash -ne $m.sha256) {
        Remove-Item $part -Force
        Fail "$($m.file): 해시 불일치로 삭제했습니다. 설치 도우미를 다시 실행하면 이 파일만 다시 받습니다."
        exit 1
    }
    Move-Item $part $dest -Force
    Ok "$($m.file)"
}
Save-State 'models' 'done'

# ─────────────────────────────────────────────
Step 5 '작업팩(워크플로우) 설치'
$packDir = Join-Path $Root 'workflows'
$wfDest = Join-Path $ComfyPath 'user\default\workflows'
$packFiles = @(Get-ChildItem $packDir -Filter '*.json' -ErrorAction SilentlyContinue)
if ($packFiles.Count -eq 0) {
    Warn '포함된 워크플로우가 없습니다(작업팩 준비 중). 이 단계는 건너뜁니다.'
} else {
    New-Item -ItemType Directory -Force $wfDest | Out-Null
    foreach ($f in $packFiles) {
        $d = Join-Path $wfDest $f.Name
        if ((Test-Path $d) -and (Get-FileHash $d).Hash -ne (Get-FileHash $f.FullName).Hash) {
            Copy-Item $d "$d.bak-$(Get-Date -Format yyyyMMddHHmmss)"
        }
        Copy-Item $f.FullName $d -Force
        Ok "워크플로우: $($f.Name)"
    }
}
Save-State 'workflows' 'done'

# ─────────────────────────────────────────────
Step 6 'Photoshop 플러그인'
# 플러그인(CCX)은 방금 설치한 sd-ppp 노드 안에 들어 있다. 따로 받지도, 재배포하지도 않는다.
$ccx = Join-Path $customNodes ($Manifest.plugin.file -replace '/', '\')
if (-not (Test-Path $ccx)) { Fail "플러그인 파일을 찾지 못했습니다: $ccx"; Info 'sd-ppp 노드 설치가 끝났는지 확인하세요.'; exit 1 }
$ccxHash = (Get-FileHash $ccx -Algorithm SHA256).Hash
if ($ccxHash -ne $Manifest.plugin.sha256) { Warn "검증한 버전과 다른 플러그인입니다($($ccxHash.Substring(0,8))). 설치는 진행하지만 포커스 패치는 건너뛸 수 있습니다." }
$patchScript = Join-Path $Root 'tools\patch-sdppp-focus.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $patchScript *> $null
$patchCode = $LASTEXITCODE
if ($patchCode -eq 2) {
    Info 'Creative Cloud 설치 창을 엽니다. 설치 확인 후 완료 메시지가 뜰 때까지 기다리세요.'
    Start-Process $ccx
    Read-Host '  설치가 끝났으면 Enter'
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $patchScript
if ($LASTEXITCODE -eq 0) { Save-State 'plugin' 'patched' } else { Warn '플러그인 설치/패치를 확인하지 못했습니다. 나중에 tools\patch-sdppp-focus.ps1 을 다시 실행하세요.' }
if (Get-Process Photoshop -ErrorAction SilentlyContinue) { Warn 'Photoshop이 실행 중입니다. 작업을 저장하고 직접 다시 시작해야 플러그인과 패치가 반영됩니다.' }

# ─────────────────────────────────────────────
Step 7 '연결 확인'
Info 'ComfyUI를 (다시) 시작해 주세요. 새 노드는 재시작해야 불러와집니다.'
Read-Host '  ComfyUI 화면이 뜨면 Enter'
$base = $null
foreach ($port in 8188, 8000, 8189) {
    try { Invoke-RestMethod "http://127.0.0.1:$port/system_stats" -TimeoutSec 3 | Out-Null; $base = "http://127.0.0.1:$port"; break } catch {}
}
if (-not $base) {
    Warn 'ComfyUI 서버 응답이 없습니다(8188/8000/8189). ComfyUI 설정의 포트를 확인하세요.'
} else {
    Ok "ComfyUI 서버: $base  ← SD-PPP 패널에 이 주소를 입력하세요"
    Set-Clipboard $base
    Info '  (주소를 클립보드에 복사했습니다)'
    $missing = @()
    foreach ($t in ($nodes | ForEach-Object { $_.provides } | Where-Object { $_ -notlike '(*' })) {
        try { $r = Invoke-RestMethod "$base/object_info/$t" -TimeoutSec 10; if (-not $r.$t) { $missing += $t } } catch { $missing += $t }
    }
    if ($missing.Count) { Fail "불러오지 못한 노드: $($missing -join ', ') — ComfyUI 재시작 또는 콘솔 오류를 확인하세요." }
    else { Ok '필요한 노드가 모두 로드되었습니다.' }
    Save-State 'server' $base
}

Write-Host ''
Write-Host '━━ 첫 그림 테스트 (Photoshop에서 직접 확인)' -ForegroundColor Cyan
Info '1. Photoshop → 플러그인 → SD-PPP 패널 열기 → 위 주소로 연결'
Info '2. 입력창에 한 문장 입력 후 다른 곳 클릭 → 글자가 유지되는지'
Info '3. 워크플로우 선택 → 이미지 가져오기 → 실행'
Info '4. 결과가 Photoshop 새 레이어로 들어오는지'
Info '네 가지가 되면 사용 준비 완료입니다.'
Save-State 'status' 'installed-needs-first-test'
