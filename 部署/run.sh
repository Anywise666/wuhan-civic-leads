#!/usr/bin/env bash
# 每期执行：headless 归集 -> 刷新看板 -> 同步 CloudBase -> 推送 GitHub
set -u

APP=/opt/wuhan-leads
# dsh 的 bin 用 env node，必须把 Node24 放 PATH 最前
for d in /opt/node24 /opt/node22; do
  if [ -x "$d/bin/dsh" ]; then export PATH="$d/bin:$PATH"; fi
done
cd "${APP}" || exit 1
mkdir -p logs

if [ -f /etc/wuhan-leads.env ]; then set -a; . /etc/wuhan-leads.env; set +a; fi
if [ -f "${APP}/.env" ]; then set -a; . "${APP}/.env"; set +a; fi
if [ -z "${WORKBUDDY_BRIDGE_TOKEN:-}" ]; then
  echo "$(date '+%F %T') WORKBUDDY_BRIDGE_TOKEN 未设置，跳过" >> logs/error.log
  exit 2
fi
# WorkBuddy 桥健康检查（模型走本地 8790 端口）
if ! curl -sS -o /dev/null http://127.0.0.1:8790/health 2>/dev/null; then
  echo "$(date '+%F %T') WorkBuddy 桥未就绪，尝试拉起" >> logs/error.log
  systemctl start wb-bridge.service 2>/dev/null || true
  sleep 3
fi
# 模型兜底：免费 hy4flash-free 被账号级 429 限流时，切到同名低成本 hy4flash (x0.03) 保证定时执行
PATCH=/root/.dsh/profiles/headless/cordis.patch.yml
PROBE_MODEL() {
  curl -sS --max-time 20 http://127.0.0.1:8790/v1/chat/completions \
    -H "Authorization: Bearer ${WORKBUDDY_BRIDGE_TOKEN}" -H "Content-Type: application/json" \
    --data-binary "{\"model\":\"$1\",\"messages\":[{\"role\":\"user\",\"content\":\"x\"}],\"max_tokens\":1}" 2>/dev/null
}
restore_model() {
  if [ -f "${PATCH}.fallback-bak" ]; then
    mv -f "${PATCH}.fallback-bak" "${PATCH}"
  fi
}
if PROBE_MODEL hy4flash-free | grep -qE '6004|429|频率限制|超出频率|不可用'; then
  echo "$(date '+%F %T') hy4flash-free 被限流，尝试兜底 hy4flash (x0.03)" >> logs/error.log
  if PROBE_MODEL hy4flash | grep -qE '6004|429|频率限制|超出频率|不可用'; then
    echo "$(date '+%F %T') hy4flash 也被限流，跳过本轮；下次 timer 自动重试" >> logs/error.log
    exit 0
  fi
  # 两个模型都探测通过后才临时切换；trap 保证本期结束/异常都恢复默认
  cp -a "${PATCH}" "${PATCH}.fallback-bak"
  trap restore_model EXIT
  sed -i 's/model: hy4flash-free/model: hy4flash/' "${PATCH}"
  echo "$(date '+%F %T') 已临时切换默认模型为 hy4flash (x0.03)，本期结束后恢复" >> logs/error.log
fi

LOG="logs/run-$(date +%F_%H%M).log"
find logs -name 'run-*.log' -mtime +30 -delete 2>/dev/null || true

echo "$(date '+%F %T') start" >> "${LOG}"
dsh --profile headless --permission-mode workspace-write --approval-policy never \
    < "${APP}/部署/任务.txt" >> "${LOG}" 2>&1
RC=$?

# 报告只保留最近 100 期
if [ -d 报告 ]; then
  ls -1 报告/*.md 2>/dev/null | sort | head -n -100 | while read -r old; do rm -f "$old"; done
fi

# 首轮生成看板（供 CloudBase 部署与 GitHub 推送）
if command -v python3 >/dev/null 2>&1; then
  python3 工具/生成看板.py >> "${LOG}" 2>&1 || true
  [ -f 看板/index.html ] && cp 看板/index.html index.html
fi

# 同步到腾讯云 CloudBase（国内镜像），并记录状态供页脚展示
TCB_CLI=/opt/cloudbase-cli/bin/tcb
TCB_ENV="${TCB_ENV:-whtvzzzx-d7gcnr78x597bb5ef}"
CB_OK=false
if [ -x "${TCB_CLI}" ] && [ -f 看板/index.html ]; then
  rm -rf .deploy-site && mkdir -p .deploy-site
  cp 看板/index.html .deploy-site/index.html
  for f in manifest.webmanifest sw.js icon-180.png icon-192.png icon-512.png icon-maskable-512.png go.html; do
    [ -f "$f" ] && cp "$f" .deploy-site/
  done
  if "${TCB_CLI}" hosting deploy .deploy-site -e "${TCB_ENV}" --concurrency 10 >> "${LOG}" 2>&1; then
    CB_OK=true
  else
    echo "$(date '+%F %T') cloudbase deploy failed" >> logs/error.log
  fi
  python3 - "${CB_OK}" "${TCB_ENV}" <<'PY' >> "${LOG}" 2>&1 || true
import datetime, json, sys
ok = sys.argv[1] == "true"
json.dump(
    {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
     "ok": ok, "env": sys.argv[2]},
    open("数据/cloudbase_status.json", "w", encoding="utf-8"),
    ensure_ascii=False,
)
PY
  # 带上同步状态再生成一次看板，并重新部署，保证 CloudBase 页脚也是最新状态
  if command -v python3 >/dev/null 2>&1; then
    python3 工具/生成看板.py >> "${LOG}" 2>&1 || true
    [ -f 看板/index.html ] && cp 看板/index.html index.html
    cp 看板/index.html .deploy-site/index.html 2>/dev/null
    "${TCB_CLI}" hosting deploy .deploy-site -e "${TCB_ENV}" --concurrency 10 >> "${LOG}" 2>&1 || true
  fi
fi

# 推送 GitHub（deploy key，5 次退避重试）
KEY="${APP}/.ssh_deploy_key"
[ -f "${KEY}" ] || KEY=/root/.ssh/wuhan_deploy
export GIT_SSH_COMMAND="ssh -i ${KEY} -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"
# 先同步远端再提交：两台维护机可能推过进度文档，避免 fast-forward 被拒
git fetch origin main >> "${LOG}" 2>&1 || true
git rebase origin/main >> "${LOG}" 2>&1 || {
  echo "$(date '+%F %T') rebase 失败，放弃本轮推送" >> logs/error.log
  git rebase --abort 2>/dev/null || true
}
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
