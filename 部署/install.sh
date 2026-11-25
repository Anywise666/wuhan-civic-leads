#!/usr/bin/env bash
# 服务器一次性安装：git/jq + Node22(/opt/node22) + dsh + known_hosts + deploy key + clone 仓库
set -euo pipefail

REPO="git@github.com:Anywise666/wuhan-civic-leads.git"
APP=/opt/wuhan-leads
NODE_DIR=/opt/node22
KEY=/root/.ssh/wuhan_deploy

echo "== 1. 系统依赖（CentOS 8 EOL，切 vault 源） =="
if ! command -v git >/dev/null 2>&1; then
  if [ -f /etc/yum.repos.d/CentOS-Linux-BaseOS.repo ] && ! grep -q vault.centos.org /etc/yum.repos.d/CentOS-Linux-BaseOS.repo; then
    sed -i 's|^mirrorlist=|#mirrorlist=|g; s|^#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-*.repo || true
  fi
  dnf install -y git jq openssh-clients curl ca-certificates || yum install -y git jq openssh-clients curl ca-certificates
fi

echo "== 2. Node 22 隔离安装到 ${NODE_DIR}（不动 /usr/bin/node） =="
if [ ! -x "${NODE_DIR}/bin/node" ]; then
  FILE=$(curl -fsSL https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt | awk '/linux-x64.tar.xz/{print $2; exit}')
  curl -fsSL "https://nodejs.org/dist/latest-v22.x/${FILE}" -o /tmp/node22.tar.xz
  mkdir -p "${NODE_DIR}"
  tar -xJf /tmp/node22.tar.xz -C "${NODE_DIR}" --strip-components=1
  rm -f /tmp/node22.tar.xz
fi
export PATH="${NODE_DIR}/bin:${PATH}"
echo "node: $(node -v)  npm: $(npm -v)"

echo "== 3. 安装 @deepseek-ai/dsh =="
npm install -g @deepseek-ai/dsh
dsh --version

echo "== 4. GitHub known_hosts =="
mkdir -p /root/.ssh && chmod 700 /root/.ssh
ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true
sort -u /root/.ssh/known_hosts -o /root/.ssh/known_hosts

echo "== 5. deploy key（只授权本仓库） =="
if [ ! -f "${KEY}" ]; then
  ssh-keygen -t ed25519 -N '' -C "wuhan-leads-deploy" -f "${KEY}" >/dev/null
fi
echo "----- 请把下面这行加到 GitHub 仓库 Settings → Deploy keys（勾选 Allow write access） -----"
cat "${KEY}.pub"
echo "-------------------------------------------------------------------------------------"

echo "== 6. clone 仓库 =="
export GIT_SSH_COMMAND="ssh -i ${KEY} -o IdentitiesOnly=yes"
if [ ! -d "${APP}/.git" ]; then
  git clone "${REPO}" "${APP}"
else
  git -C "${APP}" pull --rebase || true
fi
mkdir -p "${APP}/logs"
echo "完成。下一步：填 .env、手动跑一期、装 cron。"
