# 更新线上看板：把 看板\index.html 推送到 GitHub Pages 仓库
# 用法：pwsh -NoProfile -File 工具\更新线上.ps1
$ErrorActionPreference = 'Continue'
$base = 'E:\民生诉求线索智能体'
$repo = Join-Path $base '发布\github'
$ssh  = Join-Path $base '工具\ssh_github.cmd'

$env:GIT_SSH = $ssh
$env:GIT_TERMINAL_PROMPT = '0'

if (-not (Test-Path (Join-Path $repo '.git'))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $repo) | Out-Null
    git clone git@github.com:Anywise666/wuhan-civic-leads.git $repo
    if ($LASTEXITCODE -ne 0) { Write-Output 'CLONE_FAIL'; exit 1 }
}

Copy-Item (Join-Path $base '看板\index.html') (Join-Path $repo 'index.html') -Force
git -C $repo add -A
$changes = git -C $repo status --porcelain
if (-not $changes) { Write-Output 'NO_CHANGES'; exit 0 }

git -C $repo -c user.name='Anywise666' -c user.email='Anywise666@users.noreply.github.com' commit -m ("自动更新 " + (Get-Date -Format 'yyyy-MM-dd HH:mm'))
if ($LASTEXITCODE -ne 0) { Write-Output 'COMMIT_FAIL'; exit 1 }

git -C $repo push origin main
if ($LASTEXITCODE -ne 0) {
    git -C $repo pull --rebase origin main
    git -C $repo push origin main
}
Write-Output ("PUSH_EXIT=" + $LASTEXITCODE)
