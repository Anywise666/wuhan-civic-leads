# 服务器模型改造：DeepSeek API → WorkBuddy 免费额度

日期：2026-11-28。目标：服务器继续做唯一自动归集机，模型从「花 DeepSeek API 余额」改为「走本机 WorkBuddy 账号额度」，默认用**免费**模型，省钱；不把归集迁到任何个人电脑。

## 改造后架构

```
wuhan-leads.timer → wuhan-leads.service → 部署/run.sh
  → dsh --profile headless（默认模型 workbuddy/hy4flash-free）
  → dsh-llm-pi-ai 路由 → http://127.0.0.1:8790/v1（WorkBuddy 桥，systemd: wb-bridge.service）
  → WorkBuddy 上游（copilot.tencent.com / www.workbuddy.cn）
  → 写报告/台账/看板 → git fetch+rebase → push GitHub → CloudBase 部署
```

关键点：桥只监听 `127.0.0.1`，不对外；dsh 与桥在同一台服务器上，不经过公网 API Key。

## 省钱效果（实测）

| 模型 | 用途 | 积分消耗 |
|---|---|---|
| `hy4flash-free` | **当前默认**，带推理 | **0（免费）** |
| `deepseek-v4.1-flash` | 备选 | 0（额度内） |
| `glm-5.3-flash` | 备选 | 低 |
| `glm-5.3` | 曾临时用过，已弃用 | 0.01/次，且明显更慢 |

`credit: 0` 来自桥 `/v1/chat/completions` 返回的 `usage.credit`，可自行核验。

## 服务器上落地的文件（均不在 git 内）

| 路径 | 作用 |
|---|---|
| `/opt/wuhan-leads/wb-bridge/` | 桥程序 + 依赖（`.mjs`），已加进 `.gitignore` |
| `/opt/wuhan-leads/lib/tps.mjs` | 桥的相对依赖（`../lib/tps.mjs`） |
| `/root/.dsh/profiles/headless/cordis.patch.yml` | dsh 路由 + 默认模型配置（见下） |
| `/etc/systemd/system/wb-bridge.service` | 桥常驻服务（开机自启，Restart=always） |
| `/root/.workbuddy-bridge/credentials/` | 设备码登录凭据（加密，含自动刷新） |
| `/etc/wuhan-leads.env` | 只放 `WORKBUDDY_BRIDGE_TOKEN=...`，权限 600，`DEEPSEEK_API_KEY=` 已留空弃用 |

### cordis.patch.yml（headless profile）

```yaml
# WorkBuddy 桥路由；默认免费模型 hy4flash-free
- id: llm-pi-ai
  name: '@deepseek-ai/dsh-llm-pi-ai'
  config:
    providers:
      workbuddy:
        api: openai-completions
        baseURL: http://127.0.0.1:8790/v1
        apiKeyEnv: WORKBUDDY_BRIDGE_TOKEN
        models:
          - id: hy4flash-free
            name: Hy4 flash free
          - id: hy4flash
          - id: glm-5.3-flash
          - id: deepseek-v4.1-flash
          - id: glm-5.3
- id: agent-default-model
  name: '@deepseek-ai/dsh-agent-default-model'
  config:
    provider: workbuddy
    model: hy4flash-free
```

> `llm-pi-ai` 在 `dsh-base` 里已挂载（dormant），只要给 config 就会激活路由，不需要往 bundle 里加包。`apiKeyEnv` 指向环境变量名，dsh 每次请求从环境读桥令牌。

## 设备码登录（凭据丢了怎么恢复）

桥预检会提示 `no local login credential ... sign in first (POST /v1/auth/device)`。恢复步骤：

1. 在服务器上发起登录，拿到授权 URL：
   ```bash
   curl -sS -X POST http://127.0.0.1:8790/v1/auth/device \
     -H "Authorization: Bearer $WORKBUDDY_BRIDGE_TOKEN" \
     -H "Content-Type: application/json" --data-binary "{}"
   # 返回 {"state":"<STATE>","url":"https://www.workbuddy.cn/login?...","expiresAt":"..."}
   ```
2. 在浏览器打开返回的 `url`，用 WorkBuddy 账号登录（约 15 分钟内有效）。
3. 在服务器轮询，直到 `status: ready`：
   ```bash
   curl -sS -G http://127.0.0.1:8790/v1/auth/device \
     --data-urlencode "state=<STATE>" -H "Authorization: Bearer $WORKBUDDY_BRIDGE_TOKEN"
   ```
4. 凭据自动存到 `/root/.workbuddy-bridge/credentials/`，桥会自动刷新，无需重复登录。

## 故障排查

```bash
# 桥是否活着
systemctl status wb-bridge.service
tail -30 /opt/wuhan-leads/logs/wb-bridge.log

# 桥预检（凭据、区域、模型）
cd /opt/wuhan-leads/wb-bridge && node workbuddy-bridge.mjs --check

# 完整模型目录（默认只列精选 2 个）
curl -sS "http://127.0.0.1:8790/v1/models?all=1" -H "Authorization: Bearer $WORKBUDDY_BRIDGE_TOKEN"

# 真实调用核验积分
curl -sS http://127.0.0.1:8790/v1/chat/completions \
  -H "Authorization: Bearer $WORKBUDDY_BRIDGE_TOKEN" -H "Content-Type: application/json" \
  --data-binary '{"model":"hy4flash-free","messages":[{"role":"user","content":"收到"}],"max_tokens":20}'
# 看 usage.credit 是否为 0

# dsh 是否已走桥
printf '只回复四个字：路由验证。' | dsh --profile headless --permission-mode workspace-write --approval-policy never
```

## 重要修复：推送前必须先 rebase

2026-11-28 踩坑：两台维护机从本机推过进度文档（`179c9a8`），服务器本地 `origin/main` 还停在 `00aa3d0`，run.sh 直接 `git push` 被拒（`non-fast-forward`），重试 5 次全失败，数据只提交在本地、没上 GitHub。

已在 `部署/run.sh` 推送段加上：

```bash
git fetch origin main
git rebase origin/main
```

以后服务器每期都会先同步远端再提交推送，双机维护不再互相顶掉。

## 账号级 429 频率限制与熔断（2026-11-28 踩坑）

**教训**：改造验证那一轮用的是旧配置 `glm-5.3`（收费模型），147 次调用烧了约 636 积分，把「个人体验版」500 包耗尽，触发账号级 429 / code 6004「使用量已超出频率限制」，重置时间约 2026-11-29 10:59（北京）。注意这是**账号级冷却**，不是积分不足——切换模型、重试都不能立即恢复，只能等重置。`桥 /v1/quota` 显示其他裂变包还有额度也没用，因为限的是频率/账号而非总额度。

**已加熔断**：`部署/run.sh` 在启动 dsh 前先发一个最小探测请求（`hy4flash-free`，max_tokens=1），若响应含 `6004/429/频率限制/不可用`，就记一条日志并 `exit 0` 跳过本轮，下次 timer 自动重试。这样冷却期不会空跑、不会刷错误日志、也不会产生半成品。注意桥 `/health` 的 `quotaModels` 缓存按账号身份隔离、可能查不到，所以改用直接探测而非读缓存。

**默认模型已改免费**：`cordis.patch.yml` 默认 `hy4flash-free`（usage.credit=0），后续归集不再消耗积分；正常一轮约 20 次调用，远不会触发限流。教训是验证阶段别用收费模型跑完整轮。

**查看限流状态**：
```bash
curl -sS http://127.0.0.1:8790/v1/requests -H "Authorization: Bearer $WORKBUDDY_BRIDGE_TOKEN" | python3 -m json.tool | grep -A3 '"code": 6004'
tail -5 /opt/wuhan-leads/logs/error.log   # 看是否记录了“频率限制中，跳过本轮”
```

## 回滚

想退回 DeepSeek API（不推荐，费余额）：

1. 恢复备份：`/root/.dsh/profiles/headless/cordis.patch.yml.bak-workbuddy`、`/etc/wuhan-leads.env.bak-workbuddy`、`部署/run.sh.bak-workbuddy`；
2. 在 `/etc/wuhan-leads.env` 重新填 `DEEPSEEK_API_KEY`；
3. `systemctl restart wuhan-leads.timer`。
