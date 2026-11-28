# 服务器部署（DSH headless + systemd）

目标：在 Linux 服务器上每 12 小时跑一次归集，不依赖任何个人电脑。当前生产实例：`172.32.18.2`，目录 `/opt/wuhan-leads`。

## 运行架构

`wuhan-leads.timer`（08:00 / 20:00）→ `wuhan-leads.service`（oneshot）→ `部署/run.sh`
→ `dsh --profile headless` 读 `部署/任务.txt` → 写报告/台账 → 生成看板 → SSH 推 GitHub → Pages 重建。

## 关键决策（实测结论）

- **Node 24，独立装到 `/opt/node24`**：dsh 的 bin 用 `#!/usr/bin/env node`，而 `dsh` 的 engines 要求 Node ≥ 24.9；系统 Node 18 必须保持不动（现有小程序 / hannews 服务在用）。
- **dsh 必须显式带版本号安装**：`npm install -g @deepseek-ai/dsh@0.2.2-rc.5`，否则 npm 报 ETARGET（预发布版）。
- **remote 必须是 SSH**：`git@github.com:Anywise666/wuhan-civic-leads.git`；服务器到 GitHub 的 HTTPS git 通道不通，用 HTTPS 会挂起。
- **deploy key**：`/opt/wuhan-leads/.ssh_deploy_key`，公钥加到仓库 Settings → Deploy keys 并勾写权限。
- **模型走 WorkBuddy 免费额度**（2026-11-28 起）：不再用 DeepSeek API Key，改为服务器本机 WorkBuddy 桥（`wb-bridge.service`，`127.0.0.1:8790`）+ 免费模型 `hy4flash-free`。详见 [服务器WorkBuddy改造.md](服务器WorkBuddy改造.md)。`/etc/wuhan-leads.env` 只放桥令牌，权限 600，不进 git。
- **推送前先 rebase**：两台维护机都可能从本机推进度文档，run.sh 每期先 `git fetch origin main && git rebase origin/main` 再提交推送，避免 non-fast-forward 被拒。
- **报告保留最近 100 期**：`run.sh` 每期清理更早的；日志保留 30 天。

## 一次性安装

```bash
bash 部署/install.sh     # 幂等：装依赖、Node24、dsh、known_hosts、deploy key、clone、写 systemd 单元
```

然后：

1. 把脚本打印的公钥加到 GitHub 仓库 Deploy keys（Allow write access）；
2. 部署 WorkBuddy 桥并完成设备码登录（见 [服务器WorkBuddy改造.md](服务器WorkBuddy改造.md)），`/etc/wuhan-leads.env` 里写 `WORKBUDDY_BRIDGE_TOKEN=...` 并 `chmod 600`；
3. 手动验证一期：`systemctl start wuhan-leads.service`，看 `logs/run-*.log`；
4. 启用定时：`systemctl enable --now wuhan-leads.timer`。

## 验证命令

```bash
/opt/node24/bin/dsh --version
export PATH=/opt/node24/bin:$PATH && dsh --profile headless --help
systemctl list-timers wuhan-leads.timer --no-pager
tail -n 30 /opt/wuhan-leads/logs/run-*.log | tail -30
```

- **systemd 时间写法**：用 `OnCalendar=*-*-* 08,20:00`；写成 `08:00,20:00` 会被 systemd 只解析成 08:00（实测踩过）。

## 注意

- 不要在别的机器再启用 DSH 桌面调度，避免与服务器重复采集；
- 本机执行 `python 工具\更新线上.py` 前先 `git pull`，否则可能用旧台账覆盖仓库；
- CentOS 8 已 EOL：脚本只切 yum 源到 vault，不做系统升级；后续可迁 Rocky 8；
- `部署/wuhan-leads.cron` 是 cron 备选（二选一），内容与 systemd timer 等价。


