# wuhan-leads 服务器部署运维说明

## 环境事实（实测）

- 服务器：`172.32.18.2:22`，root。
  - 旧笔记本 KZ：密钥 `C:\Users\KZ\.ssh\id_ed25519`（历史路径）。
  - 家里 NUC（2026-11-28 起）：专用密钥 `C:\Users\NUC\AppData\Local\wuhan-maintain\id_ed25519`（公钥已加进服务器 `/root/.ssh/authorized_keys`，注释 `nuc-verify-2026-11-28`）。此密钥在持久目录、不在 D 盘沙箱区，权限正常。
  - 连接命令（务必带 `IdentitiesOnly=yes`，否则 SSH 会尝试 agent 里其他密钥导致 Permission denied）：
    ```
    ssh -o IdentitiesOnly=yes -i C:\Users\NUC\AppData\Local\wuhan-maintain\id_ed25519 root@172.32.18.2
    ```
    Windows 自带 OpenSSH 在 `C:\Windows\System32\OpenSSH\ssh.exe`。
- 系统：CentOS 8.5.2111，glibc 2.28，kernel 4.18（Node 官方 Tier 1 最低线，刚好够）
- 硬件：40 核 / 30G 内存 / 66G 可用磁盘
- **隔离安装**：Node **v24.22.3** 在 `/opt/node24`，dsh `0.2.2-rc.5` 全局装在其下；系统 Node 18 (`/usr/bin/node`) 不动，小程序 `/opt/aigc/server/app.js` 与 hannews `/opt/hannews-adp/server/src/app.js` 不受影响（实测两个进程仍存活、minio active）
- 工作目录：`/opt/wuhan-leads`，含 `规则/ 工具/ 数据/ reports/ logs/`
- 专用 deploy key：`/opt/wuhan-leads/.ssh_deploy_key`（公钥 `.pub`），git 配置 `/opt/wuhan-leads/.ssh_config`

## 两项已完成（2026-11-28）

1. ~~DeepSeek API Key~~ 已弃用：模型改走 WorkBuddy 免费桥（默认 `hy4flash-free`，credit=0），见 [部署/服务器WorkBuddy改造.md](部署/服务器WorkBuddy改造.md)。原 `DEEPSEEK_API_KEY` 行仍保留在 `/etc/wuhan-leads.env` 作备用，回滚方法见该文档。
2. ~~GitHub Deploy key 上线~~ 已完成：`/opt/wuhan-leads/.ssh_deploy_key` 已配 remote 并验证可推送；run.sh 推送前加 `git fetch && git rebase origin/main`，双机维护不再冲突。

## 素材同步

本地需要搬到服务器 `/opt/wuhan-leads/` 的：`规则/`、`工具/`、`数据/`、以及**任务提示词**（写成 `/opt/wuhan-leads/任务.txt`）。路径告诉我，我来搬。

## 手动跑一期

```bash
export PATH=/opt/node24/bin:$PATH
cd /opt/wuhan-leads
dsh --profile headless --permission-mode workspace-write --approval-policy never "$(cat 任务.txt)"
```

## systemd timer（已配好文件，待启用）

```bash
cp wuhan-leads.service wuhan-leads.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wuhan-leads.timer
systemctl list-timers wuhan-leads.timer      # 看下次触发时间
systemctl status wuhan-leads.service         # 看最近一次执行结果
```

改频率：编辑 `wuhan-leads.timer` 里的 `OnUnitActiveSec`，然后 `systemctl daemon-reload && systemctl restart wuhan-leads.timer`。

停掉：`systemctl stop wuhan-leads.timer && systemctl disable wuhan-leads.timer`。

## cron 替代方案（二选一，别和 timer 同时开）

```cron
0 */2 * * * cd /opt/wuhan-leads && PATH=/opt/node24/bin:$PATH DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY /etc/wuhan-leads.env | cut -d= -f2-) /opt/node24/bin/dsh --profile headless --permission-mode workspace-write --approval-policy never "$(cat /opt/wuhan-leads/任务.txt)" >> /opt/wuhan-leads/logs/cron.log 2>&1
```

## 日志

- stdout：`/opt/wuhan-leads/logs/run.log`
- stderr：`/opt/wuhan-leads/logs/error.log`
- systemd 运行记录：`journalctl -u wuhan-leads.service -n 50`

日志轮转建议在 `/etc/logrotate.d/wuhan-leads` 配 weekly + rotate 4 + compress。

## 已知坑（已验证）

- dsh 最新版 `0.2.2-rc.5` 是 prerelease，`npm install -g @deepseek-ai/dsh` 在 npm 10 下会报 ETARGET；必须显式带版本 `npm install -g @deepseek-ai/dsh@0.2.2-rc.5`。
- 该版 engines 要求 `node >=24.9.0`，所以必须装在 `/opt/node24`，22 虽然有 `--help` 能跑但不保证稳定。
- headless 官方支持 stdin：`echo "任务" | dsh --profile headless`；`--permission-mode` 和 `--approval-policy never` 实测是合法 flag。
- 服务器 SSH 主机指纹警告（非量子安全密钥交换）可忽略，不影响功能。
