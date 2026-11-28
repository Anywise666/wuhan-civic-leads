# 笔记本：把 DSH 桌面客户端配成 WorkBuddy 模型

目标：笔记本上已装并登录 WorkBuddy 桌面端 + 已装 DSH 桌面版 App，让桌面 App 的模型选择器里多出 WorkBuddy 分组，走 WorkBuddy 账号额度，**不需要 DeepSeek API Key，也不需要手机远程**。

## 前置条件（你已满足）

1. WorkBuddy 桌面端已安装且已用微信/手机号登录（插件会自动复用它的登录态）。
2. DSH 桌面版 App 已安装（版本 0.2.2-rc.5）。
3. 笔记本能联网（安装时从 GitHub/npm 拉包）。

## 核心结论先说

本机实测：`dsh plugin --profile desktop add ...` 这条命令行路径**在当前 0.2.2-rc.5 上被拒绝**，报错：

```
error: profile "desktop" is managed exclusively by the Electron application
```

所以 desktop profile 只能走 **DSH 桌面 App 的设置界面** 安装插件。下面的步骤按界面操作写。

## 操作步骤

### 第 1 步：把安装包拷到笔记本

台式机上的安装包路径：

```
D:\dsh\dsh-plugin-workbuddy-1.24.7.tgz
```

SHA-256（校验值）：
```
f3d32fede9943b00ab544efdf6cf1773abe0560ceeae0dc9f91b487bb8e63d4b
```

拷到笔记本任意位置，例如 `D:\dsh\dsh-plugin-workbuddy-1.24.7.tgz`。用 tgz 本地包最省事，不用等 GitHub 拉取，也不用授权构建。

### 第 2 步：在 DSH 桌面 App 里安装插件

打开 DSH 桌面版 App → 进入 **设置（Settings）→ 插件（Plugins）→ 添加插件（Add Plugin）**。

安装源填本地 tgz 路径：

```
D:\dsh\dsh-plugin-workbuddy-1.24.7.tgz
```

> 备选：如果界面允许填 GitHub 源，也可以填 `github:Ianzhyh/workbuddy-to-dsh`，但它需要联网拉源码且可能触发构建授权，首选上面的本地 tgz。

等待安装完成（pnpm 拉 41 个依赖，约十几秒）。

### 第 3 步：完全重启 DSH 桌面 App

插件的 bundle 与模型路由**只在启动时组装**，装完必须重启一次：

1. 右下角托盘区找到 DeepSeek Harness 图标，右键 → 退出（确保进程真的结束，不是只关窗口）。
2. 重新打开 DSH 桌面版 App。

### 第 4 步：确认模型已出现

重启后：

1. 在聊天界面打开模型选择器，应看到 **WorkBuddy** 分组，含 `deepseek-v4.1-flash` / `deepseek-v4-pro` / `glm-5.3` 等（模型清单跟随你 WorkBuddy 账号的上游目录，可能和台式机略有不同）。
2. 设置里应多出 **设置 → WorkBuddy** 面板，可看账号、用量、请求记录。
3. 因为 WorkBuddy 桌面端已登录，桥会自动复用登录态，无需再登录。

### 第 5 步：设为默认模型（可选）

如果想让 WorkBuddy 模型成为默认（和台式机一致），需编辑 desktop profile 的 patch 文件：

```
C:\Users\NUC\.dsh\profiles\desktop\cordis.patch.yml
```

注意：**笔记本上的用户名可能不是 NUC**，路径里的 `C:\Users\NUC` 要换成笔记本实际用户名。

把第一条 `agent-default-model` 的 config 改为：

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: workbuddy
    model: hy4flash-free
```

> 不设默认也行——每次在模型选择器里手动选 WorkBuddy 分组即可。设默认的话，注意 desktop profile 由桌面 App 管理，直接改 patch 文件可能被 App 覆盖，改完重启验证一下是否生效。

## 验证是否成功

| 检查点 | 预期 |
|---|---|
| 模型选择器 | 有 WorkBuddy 分组和模型 |
| 设置 → WorkBuddy 面板 | 显示账号已登录、来源 desktop |
| 发一条消息 | 正常回复，走 WorkBuddy 额度 |
| DEEPSEEK_API_KEY | 不需要配置 |

## 常见问题

- **模型没出现**：重启一次 App；确认 WorkBuddy 桌面端处于登录状态。
- **401 / 授权失效**：在 设置 → WorkBuddy → 账号 里重新登录。
- **安装报错 build 授权**：说明走了 GitHub 源码源，改用本地 tgz。
- **命令行装不进去**：正常，desktop profile 被 Electron 独占，必须走界面。

## 风险提示（和台式机一致）

- 这是社区插件（Ianzhyh/workbuddy-to-dsh v1.24.7），非官方，依赖 WorkBuddy 未公开协议；上游改协议可能导致失效，需更新插件。
- 只驱动本机已登录账号，消耗你自己的 WorkBuddy 额度；不要做多账号池化或转售，容易触发风控。
- 桥只绑 127.0.0.1，不要改成 0.0.0.0。
- 没有 embedding / RAG 能力（上游不提供 embedding 模型）。
