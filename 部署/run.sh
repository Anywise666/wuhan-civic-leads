#!/usr/bin/env bash
# 每期执行：headless 归集 -> 刷新看板 -> 推送到 GitHub
set -u

APP=/opt/wuhan-leads
# 自动选择 Node 24/22（dsh 的 bin 用 env node，必须把它放 PATH 最前）
for d in /opt/node24 /opt/node22; do
  if [ -x "$d/bin/dsh" ]; then export PATH="$d/bin:$PATH"; fi
done
cd "${APP}" || exit 1
mkdir -p logs

if [ -f /etc/wuhan-leads.env ]; then set -a; . /etc/wuhan-leads.env; set +a; fi
if [ -f "${APP}/.env" ]; then set -a; . "${APP}/.env"; set +a; fi
if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
  echo "$(date '+%F %T') DEEPSEEK_API_KEY 未设置，跳过" >> logs/error.log
  exit 2
fi

LOG="logs/run-$(date +%F_%H%M).log"
find logs -name 'run-*.log' -mtime +30 -delete 2>/dev/null || true

echo "$(date '+%F %T') start" >> "${LOG}"
dsh --profile headless --permission-mode workspace-write --approval-policy never \
    < "${APP}/部署/任务.txt" >> "${LOG}" 2>&1
RC=$?

# 刷新看板（Python 3.6 兼容）
if command -v python3 >/dev/null 2>&1; then
  python3 工具/生成看板.py >> "${LOG}" 2>&1 || true
  [ -f 看板/index.html ] && cp 看板/index.html index.html
fi

# 只保留最近 100 期报告
if [ -d 报告 ]; then
  ls -1 报告/*.md 2>/dev/null | sort | head -n -100 | while read -r old; do
    rm -f "$old"
  done
fi

# 同步到腾讯云 CloudBase（国内镜像，失败不影响主流程）
TCB_CLI=/opt/cloudbase-cli/bin/tcb
TCB_ENV="${TCB_ENV:-whtvzzzx-d7gcnr78x597bb5ef}"
if [ -x "${TCB_CLI}" ] && [ -f 看板/index.html ]; then
  rm -rf .deploy-site && mkdir -p .deploy-site
  cp 看板/index.html .deploy-site/index.html
  for f in manifest.webmanifest sw.js icon-180.png icon-192.png icon-512.png icon-maskable-512.png go.html; do
    [ -f "$f" ] && cp "$f" .deploy-site/
  done
  "${TCB_CLI}" hosting deploy .deploy-site -e "${TCB_ENV}" --concurrency 10 >> "${LOG}" 2>&1 \
    || echo "$(date '+%F %T') cloudbase deploy failed" >> logs/error.log
fi

# 推送（deploy key：优先用仓库目录里的，其次 /root/.ssh/wuhan_deploy）
KEY="${APP}/.ssh_deploy_key"
[ -f "${KEY}" ] || KEY=/root/.ssh/wuhan_deploy
export GIT_SSH_COMMAND="ssh -i ${KEY} -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"
git add -A >> "${LOG}" 2>&1
if ! git diff --cached --quiet; then
  git -c user.name="wuhan-leads-agent" -c user.email="agent@users.noreply.github.com" \
      commit -m "自动归集 $(date '+%F %H:%M')" >> "${LOG}" 2>&1
  pushed=0
  for attempt in 1 2 3 4 5; do
    if git push origin main >> "${LOG}" 2>&1; then pushed=1; break; fi
    echo "$(date '+%F %T') push attempt ${attempt} failed" >> logs/error.log
    sleep $((attempt * 10))
  done
  [ "${pushed}" = "1" ] || echo "$(date '+%F %T') push failed after retries; next run retries" >> logs/error.log
fi

echo "$(date '+%F %T') done rc=${RC}" >> "${LOG}"
exit ${RC}


