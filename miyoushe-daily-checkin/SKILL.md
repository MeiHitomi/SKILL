---
name: miyoushe-daily-checkin
description: Automate daily check‑in for Miyoushe Genshin Impact and Honkai:Star Rail. Require user provide web cookie. Use when user asks for miyoushe daily sign‑in, genshin/hsr auto checkin.
description-cn: 米游社（原神 + 崩坏：星穹铁道）每日签到自动化。调用米游社 Luna 签到接口完成国服游戏每日签到，需用户自行提供网页端 Cookie。当用户要求「米游社签到」「原神/星铁每日签到」「自动签到」「封装米游社签到 skill」或使用米游社福利签到相关任务时使用。
agent_created: true
---

# 米游社每日签到

## Overview

本 skill 提供米游社（国服）四款游戏——**原神、崩坏：星穹铁道、崩坏3、绝区零**——的每日签到能力。底层是一个纯 Python 标准库脚本（`scripts/miyoushe_sign.py`），通过米游社 Luna 签到接口完成请求，并自动拉取账号下绑定的角色逐个签到。

**Cookie 由用户自行填写**：脚本不内置任何账号凭据，必须在运行前由用户把米游社网页端 Cookie 填入配置文件。Cookie 缺失时，skill 会提示用户，而不会尝试自动获取。

## When to Use

- 用户要求「米游社签到」「原神/星铁每日签到」「帮我自动签到」等。
- 用户希望把米游社每日签到封装为可复用能力（skill）。
- 用户已在别处配置好 Cookie，要求跑一次签到或接入定时任务。

## Workflow

执行签到或配置时，按以下顺序操作：

### 1. 定位 skill 与脚本

读取本 skill 目录下的 `scripts/miyoushe_sign.py`。脚本路径相对于本 SKILL.md：`<skill_dir>/scripts/miyoushe_sign.py`。

### 2. 准备运行目录

默认工作目录为 `D:\miyoushe_sign`（遵循用户「产物不落 C 盘」的偏好）。若以下文件不存在，则从 skill 资源复制过去：

- 复制 `scripts/miyoushe_sign.py` → `D:\miyoushe_sign\miyoushe_sign.py`
- 复制 `scripts/config.example.json` → `D:\miyoushe_sign\config.json`（首次创建）

如工作目录已存在 `miyoushe_sign.py`，可直接复用，无需覆盖（除非用户要求更新脚本）。

### 3. 确认 Cookie（用户自行填写）

读取 `D:\miyoushe_sign\config.json` 的 `cookie` 字段：

- 若为空或仍为占位提示文本，**不要尝试自动获取 Cookie**。通过 `AskUserQuestion` 或直接询问用户，让其粘贴米游社网页端 Cookie（需包含 `ltoken` 与 `ltuid`；`cookie_token`、`account_id` 建议一并带上）。
- 获取方法见 `references/api.md` 的「获取 Cookie」一节。
- 用户粘贴后，将其写入 `config.json` 的 `cookie` 字段并保存。
- `device_id` 字段留空即可，脚本会基于 cookie 自动用 uuid3 生成稳定设备 ID。

### 4. 运行脚本

使用受管 Python 解释器执行：

```
C:\Users\57799\.workbuddy\binaries\python\versions\3.13.12\python.exe D:\miyoushe_sign\miyoushe_sign.py
```

脚本输出末尾以 `---SUMMARY---` 段落汇总每行结果，前缀含义：

- `OK  |` 签到成功
- `SKIP|` 今天已签到过（含 `retcode=-5003`）
- `FAIL|` 签到失败，附 `retcode` 与 `message`

### 5. 结果处理与排错

- 全部 `OK/SKIP`：向用户播报签到成功。
- 出现 `FAIL`：读取 `references/api.md` 的「常见 retcode 与排错」一节，按 `retcode` 给出建议。
  - **特别注意 `-500012活动已结束`具有强误导性**：它通常意味着 DS 签名格式不对或缺少
    `x-rpc-signgame` 头，**而非活动下线**。排查时先做对照实验（换用确定有效的 act_id，
    如星铁 `e202304121516551`）：若对照组成功，则问题在签名或该游戏的 `signgame` 头。
    各游戏 signgame：原神 `hk4e`、星铁 `hkrpg`、绝区零 `zzz`、崩3 **不设**。
  - 脚本抛 `cookie 字段为空`：回到第 3 步请用户补填。

### 6. 接入每日自动化（可选）

如需无人值守每日签到，可为用户创建一个递归自动化：每天固定时间运行第 4 步的命令，并把 `---SUMMARY---` 结果通过 Agent Mail 推送；Cookie 缺失时仅在对话提示、不发邮件。自动化 ID 与脚本路径需在创建时记录。

## Resources

### scripts/

- `miyoushe_sign.py`：签到主脚本（纯标准库，无第三方依赖）。含 DS 动态签名、角色拉取、双游戏签到、SUMMARY 汇总。如需修改接口/活动 ID/签名 salt，参见 `references/api.md`。
- `config.example.json`：配置模板，复制到 `D:\miyoushe_sign\config.json` 后填写 `cookie`。

### references/

- `api.md`：米游社签到接口的权威参数（域名、Luna 签到地址、各游戏 act_id、game_biz、DS salt、User-Agent、关键请求头），以及 Cookie 获取步骤、常见 retcode 含义与排错指南。维护脚本时以此为准。

