# 米游社签到接口参考（维护脚本时以此为准）

本文件记录米游社（国服）每日签到所依赖的接口参数、签名算法与排错方法。脚本 `scripts/miyoushe_sign.py` 中的常量必须与本文件保持一致；若米游社官方更新，按本文件核对并同步修改脚本顶部的常量。

## 域名与接口

基础域名：`https://api-takumi.mihoyo.com`

| 用途 | 方法 | 路径 |
|------|------|------|
| 拉取绑定角色 | GET | `/binding/api/getUserGameRolesByCookie?game_biz=<game_biz>` |
| 查询今日是否已签到 | GET | `/event/luna/info?lang=zh-cn&act_id=<act_id>&region=<region>&uid=<uid>` |
| 执行签到 | POST | `/event/luna/sign` |

签到 POST 请求体：`{"act_id": "<act_id>", "region": "<region>", "uid": "<uid>"}`（JSON）。

## 各游戏参数

| 游戏 | act_id | game_biz | x-rpc-signgame |
|------|--------|----------|----------------|
| 原神 | `e202311201442471` | `hk4e_cn` | `hk4e` |
<<<<<<< HEAD
| 崩坏：星穹铁道 | `e202304121516551` | `hkrpg_cn` | `hkrpg` |
| 崩坏3 | `e202306201626331` | `bh3_cn` | （无需设置） |
| 绝区零 | `e202406242138391` | `nap_cn` | `zzz`（**独立域名** `act-nap-api.mihoyo.com`，路径 `/event/luna/zzz`） |

> 注意：旧版接口 `/event/bbs_sign_reward/sign` 与旧的原神 act_id `e202009291139501` 已失效，会导致 `retcode=-10001`。当前统一使用 `/event/luna/sign` 与上述 act_id。
>
> **原神 act_id `e202311201442471` 一直有效**，若它报 `-500012`，根因是签名或 `x-rpc-signgame` 头缺失（见下方排错），**不是活动下线**。
=======
| 崩坏：星穹铁道 | `e202304121516551` | `hkrpg_cn` | （无需设置） |

> 注意：旧版接口 `/event/bbs_sign_reward/sign` 与旧的原神 act_id `e202009291139501` 已失效，会导致 `retcode=-10001`。当前统一使用 `/event/luna/sign` 与上述 act_id。
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d

## DS 动态签名（web 端）

- 签名 salt：`d9200c846b10886e8c874fc33c8f308b`（与米游社网页客户端一致）。
- 算法：`DS = "t,r,md5(salt=<salt>&t=<t>&r=<r>)"`
  - `t` = 当前 Unix 时间戳（秒）
  - `r` = 6 位随机字符串（小写字母 + 数字）
  - **关键点**：签名串结尾为 `&r=<r>`，**不要**追加 `&b=` 或 `&q=` 等额外字段（空字段会改变 MD5 结果）。
- 该 salt 可能随米游社版本轮换，官方更换时同步更新脚本 `WEB_SALT` 常量。

## 关键请求头

| 头 | 值 |
|----|----|
| `User-Agent` | `Mozilla/5.0 (Linux; Android 12; Unspecified Device) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36 miHoYoBBS/2.109.0` |
| `x-rpc-app_version` | `2.109.0` |
| `x-rpc-client_type` | `5`（移动端 web） |
| `x-rpc-channel` | `miyousheluodi` |
| `X-Requested-With` | `com.mihoyo.hyperion` |
| `Referer` | 签到/查询用 `https://act.mihoyo.com/`；拉取角色用 `https://webstatic.mihoyo.com/` |
| `Origin`（签到/查询） | `https://act.mihoyo.com` |
| `Content-Type`（POST） | `application/json` |
| `x-rpc-device_id` | 由 cookie 经 `uuid.uuid3(uuid.NAMESPACE_URL, cookie)` 生成，保持稳定 |

## 获取 Cookie（用户自行完成）

1. 浏览器无痕打开 `https://user.mihoyo.com/` 并登录米哈游账号。
2. **方法 A（应用面板）**：F12 → 应用 → 存储 → Cookie → `https://user.mihoyo.com`，复制 `ltoken`、`ltuid`、`account_id`、`cookie_token`，拼成：`ltuid=...; ltoken=...; account_id=...; cookie_token=...`。
3. **方法 B（请求头）**：F12 → 网络 → 筛选 XHR/Fetch → 刷新页面 → 点任一 `api-takumi.mihoyo.com` 请求 → 请求标头 → 复制 `Cookie` 整串。
4. **方法 C（最快）**：控制台输入 `document.cookie` 回车（可能缺 HttpOnly 的 `cookie_token`，但签到通常只需 `ltoken` + `ltuid`）。

Cookie 失效后需重新抓取；填入 `config.json` 的 `cookie` 字段即可。

## 常见 retcode 与排错

| retcode | 含义 / 处理 |
|---------|-------------|
| `0` | 签到成功 |
| `-5003` | 今天已签到过（视为 SKIP，无需处理） |
<<<<<<< HEAD
| `-500012` 活动已结束 | **高概率是 DS 签名错误或缺少 `x-rpc-signgame` 头**，而非活动真的下线。用同一 Cookie + 星铁 act_id 做对照：若星铁成功则说明 Cookie/网络正常，问题在签名或该游戏的 signgame 头。 |
| `-500001` 网络出小差 | act_id 无效或接口异常 |
=======
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d
| `-10001` invalid request | 「请求头字段缺失或错误」。多为接口地址 / act_id / salt / UA / app_version 过期，或 DS 格式错误。按本文件核对脚本常量是否为最新；也可能因系统时间偏差过大，校准时间后重试 |
| `-100` / `10001` | Cookie 失效，重新抓取 |
| `1034` | 触发验证码（米游社风控）。需人工在米游社完成验证，或稍后重试 |
| `-1` | 通用错误，稍后重试 |

<<<<<<< HEAD
### 排错铁律（2026-10-10 血泪教训）

`retcode=-500012活动已结束` 这个提示**极具误导性**。实测确认：即使 act_id 完全有效、活动正常开放，只要 DS 签名格式不对或缺少 `x-rpc-signgame` 头，一样会返回 `-500012`。

因此排查顺序必须是：
1. **先做对照实验**：同一份Cookie 换用一个确定有效的 act_id（如星铁 `e202304121516551`）发请求。
   - 若对照组也失败 → Cookie 过期或网络问题。
   - 若对照组成功 → 问题在当前游戏的 `act_id` / `signgame` 头 / DS 签名。
2. **再对比是否漏了 `x-rpc-signgame` 头**：原神必须带 `hk4e`，绝区零必须带 `zzz`，
   崩3 **不带**。带与不带会返回完全不同的 retcode。
3. **最后才怀疑 act_id 失效或活动下线**——这一步应该在前面几步都排除后才做。

> 踩坑实例：曾把 `-500012` 直接判定为「官方关闭签到活动」，据此给用户建议精简绑定列表，
> 结果方向完全错误——真实原因是脚本用了 DS v2 格式（salt 开头 + `&b=`/`&q=` 段）
> 而签到接口只认 web v1 格式（`salt=` 前缀 + 仅 `t`/`r`）。换回 v1 后原神当天即签到成功。

=======
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d
> 说明：本 skill 仅用于用户自有账号的便利性自动化，请仅对自己拥有的账号使用。
