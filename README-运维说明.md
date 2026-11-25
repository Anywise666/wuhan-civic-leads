# wuhan-leads 服务器部署运维说明

## 环境事实（实测）

- 服务器：`172.32.18.2:22`，root，密钥 `~/.ssh/id_ed25519`（本地 Windows 路径 `C:\Users\KZ\.ssh\id_ed25519`）
- 系统：CentOS 8.5.2111，glibc 2.28，kernel 4.18（Node 官方 Tier 1 最低线，刚好够）
- 硬件：40 核 / 30G 内存 / 66G 可用磁盘
- **隔离安装**：Node **v24.22.3** 在 `/opt/node24`，dsh `0.2.2-rc.5` 全局装在其下；系统 Node 18 (`/usr/bin/node`) 不动，小程序 `/opt/aigc/server/app.js` 与 hannews `/opt/hannews-adp/server/src/app.js` 不受影响（实测两个进程仍存活、minio active）
- 工作目录：`/opt/wuhan-leads`，含 `规则/ 工具/ 数据/ reports/ logs/`
- 专用 deploy key：`/opt/wuhan-leads/.ssh_deploy_key`（公钥 `.pub`），git 配置 `/opt/wuhan-leads/.ssh_config`

## 还差你做的两件事（阻塞项）

1. **DeepSeek API Key**：把 key 写入服务器 `/etc/wuhan-leads.env`：
   ```
   DEEPSEEK_API_KEY=sk-你的key
   ```
   权限 `chmod 600`。不进代码、不进 git。
2. **GitHub Deploy key 上线**：把 `/opt/wuhan-leads/.ssh_deploy_key.pub` 的内容贴到目标仓库 `Settings → Deploy keys → Add deploy key`，**勾选 "Allow write access"**。仓库地址告诉我，我配 remote。

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
