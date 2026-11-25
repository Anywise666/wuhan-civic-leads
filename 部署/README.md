# 服务器部署（DSH headless + cron）

目标：在 Linux 服务器上每 12 小时跑一次归集，不依赖任何个人电脑。

## 决策（与 WorkBuddy 盘点一致）

- Node：独立装到 `/opt/node22`，**不动** `/usr/bin/node`（现有小程序 / hannews 服务继续用 18）；
- 运行目录：`/opt/wuhan-leads`（从 GitHub clone，含规则/工具/数据/报告）；
- 触发：cron（或 systemd timer），每 12 小时一次，可改 2 小时；
- 推送：服务器生成 deploy key，只对 `Anywise666/wuhan-civic-leads` 有写权限；
- 凭据：`/opt/wuhan-leads/.env` 存 `DEEPSEEK_API_KEY`，权限 600，不进 git。

## 一次性安装

```bash
# 以 root 执行；脚本幂等，可重复跑
bash 部署/install.sh
```

脚本会：装 git/jq（CentOS 8 走 vault 源）→ 下载 Node 22 到 `/opt/node22` → 装 `@deepseek-ai/dsh` →
写 GitHub known_hosts → 生成 deploy key → clone 仓库到 `/opt/wuhan-leads`。

然后：

1. 把脚本打印的公钥加到 GitHub 仓库 **Settings → Deploy keys**，勾选 **Allow write access**；
2. 填 API Key：`echo 'DEEPSEEK_API_KEY=sk-xxx' > /opt/wuhan-leads/.env && chmod 600 /opt/wuhan-leads/.env`；
3. 手动跑一期：`/opt/wuhan-leads/部署/run.sh`；
4. 确认 `报告/`、`数据/`、`index.html` 有更新且已推送，再装 cron：

```bash
cp /opt/wuhan-leads/部署/wuhan-leads.cron /etc/cron.d/wuhan-leads
chmod 644 /etc/cron.d/wuhan-leads
```

## 验证命令

```bash
/opt/node22/bin/dsh --version
/opt/node22/bin/dsh --profile headless --help
/opt/node22/bin/dsh --profile headless "回答两个字：收到"
```

## 注意

- `dsh --profile headless` 是**单次任务**：执行、打印、退出，不开端口；
- 任务文本从 stdin 传入（`< 部署/任务.txt`），比超长命令行参数稳；
- 无人值守用 `--approval-policy never`，避免卡在人工审批；
- CentOS 8 已 EOL：本脚本只切 yum 源到 vault，不做系统升级；后续可迁 Rocky 8；
- 日志在 `/opt/wuhan-leads/logs/`，按天清理由 `run.sh` 处理。

