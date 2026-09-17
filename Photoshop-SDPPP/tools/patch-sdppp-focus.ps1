# SD-PPP 2.0.0 입력창 포커스 패치
# 알려진 원본 해시일 때만 적용하고, 결과 해시까지 확인한다. 모르는 버전은 건드리지 않는다.
param(
    [switch]$Restore,
    [string[]]$Path,             # 테스트용: 특정 photoshop.html 지정
    [string]$ManifestPath = (Join-Path $PSScriptRoot '..\manifest.json')
)
$ErrorActionPreference = 'Stop'

$manifest = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$patch = $manifest.plugin.focus_patch

function Find-SdpppHtml {
    $roots = @(
        (Join-Path $env:APPDATA 'Adobe\UXP\Plugins\External'),
        (Join-Path ${env:CommonProgramFiles} 'Adobe\UXP\Plugins\External')
    )
    foreach ($r in $roots) {
        if (-not (Test-Path $r)) { continue }
        Get-ChildItem $r -Directory -Filter "$($manifest.plugin.id)_*" | ForEach-Object {
            $f = Join-Path $_.FullName ($patch.target -replace '/', '\')
            if (Test-Path $f) { $f }
        }
    }
}

$targets = if ($Path) { @($Path) } else { @(Find-SdpppHtml) }
if ($targets.Count -eq 0) {
    Write-Host '  [대기] 설치된 SD-PPP 플러그인을 찾지 못했습니다. Creative Cloud 설치를 먼저 끝내주세요.' -ForegroundColor Yellow
    exit 2
}

$result = 0
foreach ($file in $targets) {
    $hash = (Get-FileHash $file -Algorithm SHA256).Hash
    $backup = "$file.orig"

    if ($Restore) {
        if ((Test-Path $backup) -and (Get-FileHash $backup -Algorithm SHA256).Hash -eq $patch.before_sha256) {
            Copy-Item $backup $file -Force
            Write-Host "  [복원] 원본으로 되돌렸습니다: $file" -ForegroundColor Green
        } else {
            Write-Host "  [건너뜀] 확인된 원본 백업이 없습니다: $file" -ForegroundColor Yellow
            $result = 1
        }
        continue
    }

    if ($hash -eq $patch.after_sha256) {
        Write-Host '  [완료] 포커스 패치가 이미 적용되어 있습니다.' -ForegroundColor Green
        continue
    }
    if ($hash -ne $patch.before_sha256) {
        Write-Host "  [중단] 알 수 없는 SD-PPP 버전이라 패치하지 않습니다. ($hash)" -ForegroundColor Yellow
        Write-Host '         설치기에 포함된 CCX로 다시 설치한 뒤 재시도하세요.'
        $result = 1
        continue
    }

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $text = [System.IO.File]::ReadAllText($file, $utf8)
    $idx = $text.IndexOf($patch.remove, [System.StringComparison]::Ordinal)
    if ($idx -lt 0 -or $text.IndexOf($patch.remove, $idx + 1, [System.StringComparison]::Ordinal) -ge 0) {
        Write-Host '  [중단] 패치 위치가 정확히 한 곳이 아닙니다. 파일을 바꾸지 않았습니다.' -ForegroundColor Red
        $result = 1
        continue
    }

    Copy-Item $file $backup -Force
    $tmp = "$file.patching"
    [System.IO.File]::WriteAllText($tmp, $text.Remove($idx, $patch.remove.Length), $utf8)
    if ((Get-FileHash $tmp -Algorithm SHA256).Hash -ne $patch.after_sha256) {
        Remove-Item $tmp -Force
        Write-Host '  [중단] 패치 결과 해시가 달라 적용을 취소했습니다. 원본은 그대로입니다.' -ForegroundColor Red
        $result = 1
        continue
    }
    Move-Item $tmp $file -Force
    Write-Host '  [완료] 포커스 패치 적용. Photoshop을 다시 시작하면 반영됩니다.' -ForegroundColor Green
}
exit $result
