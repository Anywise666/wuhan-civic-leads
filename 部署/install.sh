#!/usr/bin/env bash
# 服务器一次性安装：git/jq + Node24(/opt/node24) + dsh + known_hosts + deploy key + clone + systemd
# 注意：dsh 的 bin 用 `#!/usr/bin/env node`，运行时必须把 /opt/node24/bin 放在 PATH 最前。
set -euo pipefail

REPO="git@github.com:Anywise666/wuhan-civic-leads.git"
APP=/opt/wuhan-leads
NODE_DIR=/opt/node24
KEY="${APP}/.ssh_deploy_key"
DSH_VERSION="0.2.2-rc.5"   # 预发布版必须显式带版本号，否则 npm 报 ETARGET

echo "== 1. 系统依赖（CentOS 8 EOL，切 vault 源） =="
if ! command -v git >/dev/null 2>&1; then
  if [ -f /etc/yum.repos.d/CentOS-Linux-BaseOS.repo ] && ! grep -q vault.centos.org /etc/yum.repos.d/CentOS-Linux-BaseOS.repo; then
    sed -i 's|^mirrorlist=|#mirrorlist=|g; s|^#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-*.repo || true
  fi
  dnf install -y git jq openssh-clients curl ca-certificates || yum install -y git jq openssh-clients curl ca-certificates
fi

echo "== 2. Node 24 隔离安装到 ${NODE_DIR}（不动 /usr/bin/node） =="
if [ ! -x "${NODE_DIR}/bin/node" ]; then
  FILE=$(curl -fsSL https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt | awk '/linux-x64.tar.xz/{print $2; exit}')
  curl -fsSL "https://nodejs.org/dist/latest-v24.x/${FILE}" -o /tmp/node24.tar.xz
  mkdir -p "${NODE_DIR}"
  tar -xJf /tmp/node24.tar.xz -C "${NODE_DIR}" --strip-components=1
  rm -f /tmp/node24.tar.xz
fi
export PATH="${NODE_DIR}/bin:${PATH}"
echo "node: $(node -v)  npm: $(npm -v)"

echo "== 3. 安装 @deepseek-ai/dsh =="
npm install -g "@deepseek-ai/dsh@${DSH_VERSION}"
dsh --version

echo "== 4. GitHub known_hosts =="
mkdir -p /root/.ssh && chmod 700 /root/.ssh
ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true
sort -u /root/.ssh/known_hosts -o /root/.ssh/known_hosts

echo "== 5. deploy key（只授权本仓库） =="
mkdir -p "${APP}"
if [ ! -f "${KEY}" ]; then
  ssh-keygen -t ed25519 -N '' -C "wuhan-leads-deploy" -f "${KEY}" >/dev/null
fi
echo "----- 请把下面这行加到 GitHub 仓库 Settings → Deploy keys（勾选 Allow write access） -----"
cat "${KEY}.pub"
echo "-------------------------------------------------------------------------------------"

echo "== 6. clone 仓库（首次用公开 HTTPS，之后切 SSH） =="
export GIT_SSH_COMMAND="ssh -i ${KEY} -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"
if [ ! -d "${APP}/.git" ]; then
  git clone https://github.com/Anywise666/wuhan-civic-leads.git "${APP}"
fi
git -C "${APP}" remote set-url origin "${REPO}"
mkdir -p "${APP}/logs"

echo "== 7. systemd 单元（不改现有服务） =="
cat > /etc/systemd/system/wuhan-leads.service <<'EOF'
[Unit]
Description=Wuhan Leads collector (one-shot, triggered by timer)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/wuhan-leads
Environment=PATH=/opt/node24/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
EnvironmentFile=-/etc/wuhan-leads.env
ExecStart=/bin/bash /opt/wuhan-leads/部署/run.sh
TimeoutStartSec=3600
StandardOutput=append:/opt/wuhan-leads/logs/run.log
StandardError=append:/opt/wuhan-leads/logs/error.log
EOF
cat > /etc/systemd/system/wuhan-leads.timer <<'EOF'
[Unit]
Description=Run Wuhan Leads collector every 12 hours

[Timer]
OnCalendar=*-*-* 00,12:15:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload

echo
echo "剩余两步（手工）："
echo "  1) 填 API Key：echo 'DEEPSEEK_API_KEY=sk-xxx' > /etc/wuhan-leads.env && chmod 600 /etc/wuhan-leads.env"
echo "  2) 验证一期：systemctl start wuhan-leads.service，看 /opt/wuhan-leads/logs/"
echo "  3) 启用定时：systemctl enable --now wuhan-leads.timer"
