#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
米游社每日签到脚本（纯标准库实现，无第三方依赖）

支持游戏（国服）：
  - 原神          hk4e_cn   act_id e202311201442471   signgame=hk4e
  - 崩坏：星穹铁道 hkrpg_cn   act_id e202304121516551   signgame=hkrpg
  - 崩坏3         bh3_cn    act_id e202306201626331
  - 绝区零        nap_cn    act_id e202406242138391   独立域名 act-nap-api

用法：python miyoushe_sign.py
配置：同目录 config.json——  {"cookie": "...", "device_id": "..."}

【重要】DS 签名说明（踩坑记录，勿改）
  米游社签到接口用的是 **web 端 v1 签名**：
      DS = "{t},{r},{md5('salt=' + SALT + '&t=' + t + '&r=' + r)}"
  签名串以 `salt=` 开头，且**不要**追加 `&b=` / `&q=` 字段。
  若误用 DS v2 格式（salt 开头+ b/q 段），服务端会返回
  `-500012 活动已结束` —— 该错误码极具误导性，实际含义是「签名校验未通过」，
  而不是活动真的下线了。
=======
米游社每日签到（原神 + 崩坏：星穹铁道）
====================================
仅依赖 Python 标准库，无需安装第三方包。

实现说明：
  - 调用米游社（api-takumi.mihoyo.com）的游戏签到接口。
  - 需要米游社网页端登录后的 Cookie（必须包含 ltoken 与 ltuid）。
  - 每次请求带 DS 动态签名（web 端 salt），以及 x-rpc-act_id / x-rpc-signgame 等头。

使用步骤：
  1. 在 config.json 中填入你的米游社网页端 Cookie（见下方说明）。
  2. 运行：python miyoushe_sign.py
  3. 查看输出；成功/失败会以 SUMMARY 段落汇总（便于自动化读取）。

获取 Cookie 的方法（米游社网页端）：
  1. 浏览器打开 https://user.mihoyo.com/ 并登录米哈游账号。
  2. 打开开发者工具（F12）→ 网络(Network) → 任意请求 → 复制 Request Headers 里的 Cookie 整串。
  3. 粘贴到 config.json 的 "cookie" 字段。
  Cookie 中需包含 ltoken、ltuid（或 account_id）；cookie_token 也建议带上。
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d
"""

import json
import time
import random
import string
import hashlib
<<<<<<< HEAD
import uuid
import urllib.request
import urllib.error
import os
import sys

# ============ 配置常量 ============
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# web 端 DS 签名 salt（与米游社网页客户端一致；官方轮换时需同步更新）
WEB_SALT = "d9200c846b10886e8c874fc33c8f308b"

APP_VERSION = "2.109.0"
CLIENT_TYPE = "5"  # 移动端 web
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 12; Unspecified Device) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36 "
    "miHoYoBBS/" + APP_VERSION
)
REFERER = "https://act.mihoyo.com/"
ORIGIN = "https://act.mihoyo.com"
TAKUMI = "https://api-takumi.mihoyo.com"
NAP_API = "https://act-nap-api.mihoyo.com"
BINDING_API = TAKUMI + "/binding/api/getUserGameRolesByCookie"

# ============ 各游戏参数（2026-10-10 实测校验通过） ============
GAME_CONFIG = {
    "hk4e_cn": {
        "name": "原神",
        "act_id": "e202311201442471",
        "signgame": "hk4e",
        "host": TAKUMI,
        "path": "/event/luna",
    },
    "hkrpg_cn": {
        "name": "崩坏：星穹铁道",
        "act_id": "e202304121516551",
        "signgame": "hkrpg",
        "host": TAKUMI,
        "path": "/event/luna",
    },
    "bh3_cn": {
        "name": "崩坏3",
        "act_id": "e202306201626331",
        "signgame": "",
        "host": TAKUMI,
        "path": "/event/luna",
    },
    "nap_cn": {
        "name": "绝区零",
        "act_id": "e202406242138391",
        "signgame": "zzz",
        "host": NAP_API,
        "path": "/event/luna/zzz",
    },
}

ERRCODE_DESC = {
    -500012: "签名校验未通过（DS 算法/salt/signgame 头不对），或活动已结束",
    -500001: "act_id 无效或接口异常",
    -5003: "今日已签到",
    -10002: "未查询到游戏角色（缺 uid/region，属正常）",
    -100: "风控校验失败",
    1034: "触发验证码，需人工在米游社完成验证",
    -10001: "请求头字段缺失或错误（接口地址/act_id/salt/UA 过期）",
}


# ============ 工具函数 ============

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"错误：未找到配置文件 - {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_ds():
    """
    生成 DS 动态签名（web 端 v1 算法）。
    格式：DS = "{t},{r},{md5}"
    签名串：salt=<WEB_SALT>&t=<t>&r=<r>
    注意：结尾是 &r=<r>，不要追加 &b= 或 &q=
    """
    t = str(int(time.time()))
    r = "".join(random.sample(string.ascii_lowercase + string.digits, 6))
    raw = "salt=" + WEB_SALT + "&t=" + t + "&r=" + r
    return t + "," + r + "," + hashlib.md5(raw.encode("utf-8")).hexdigest()


def device_id_from_cookie(cookie: str) -> str:
    """由 cookie 生成稳定设备 ID（与官方一致）"""
    return str(uuid.uuid3(uuid.NAMESPACE_URL, cookie))


def base_headers(cookie: str, device_id: str) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
=======
import urllib.request
import urllib.error
import uuid
import sys
import os

# ------------------------- 配置常量 -------------------------
# 米游社 web 端 DS 签名 salt（与米游社网页客户端一致，若官方更换需同步更新）
WEB_SALT = "d9200c846b10886e8c874fc33c8f308b"

# 各游戏配置：act_id 为当前签到活动 ID（国服），game_biz 用于拉取角色，signgame 为签名头
GAMES = {
    "genshin": {
        "name": "原神",
        "act_id": "e202311201442471",
        "game_biz": "hk4e_cn",
        "signgame": "hk4e",
    },
    "hsr": {
        "name": "崩坏：星穹铁道",
        "act_id": "e202304121516551",
        "game_biz": "hkrpg_cn",
        "signgame": "hkrpg",
    },
}

APP_VERSION = "2.109.0"
CLIENT_TYPE = "5"  # 5 = 移动端 web
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 12; Unspecified Device) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36 "
    f"miHoYoBBS/{APP_VERSION}"
)
REFERER = "https://act.mihoyo.com/"
ORIGIN = "https://act.mihoyo.com"

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


# ------------------------- 工具函数 -------------------------
def _random_text(num: int = 6) -> str:
    """生成指定长度的随机字符串（小写字母 + 数字）。"""
    return ''.join(random.sample(string.ascii_lowercase + string.digits, num))


def get_ds():
    """生成 DS 动态签名（web 端 v1 算法）。

    官方格式：DS = "t,r,md5(salt=<salt>&t=<t>&r=<r>)"
    与 MihoyoBBSTools/tools.py 中的 get_ds(web=True) 保持一致。
    """
    t = str(int(time.time()))
    r = _random_text(6)
    q = f"salt={WEB_SALT}&t={t}&r={r}"
    s = hashlib.md5(q.encode("utf-8")).hexdigest()
    return f"{t},{r},{s}"


def _device_id_from_cookie(cookie: str) -> str:
    """使用 cookie 通过 uuid v3 生成稳定的设备 ID（与官方一致）。"""
    return str(uuid.uuid3(uuid.NAMESPACE_URL, cookie))


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"未找到配置文件 {CONFIG_PATH}，请复制 config.example.json 为 config.json 并填写 Cookie。"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cookie = (cfg.get("cookie") or "").strip()
    if not cookie:
        raise ValueError("config.json 中的 cookie 字段为空，请先填入米游社网页端 Cookie。")
    device_id = (cfg.get("device_id") or "").strip() or _device_id_from_cookie(cookie)
    return cookie, device_id


def _base_headers(cookie: str, device_id: str) -> dict:
    """构造通用请求头。"""
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d
        "Accept-Language": "zh-CN,en-US;q=0.8",
        "Cookie": cookie,
        "User-Agent": USER_AGENT,
        "X-Requested-With": "com.mihoyo.hyperion",
        "x-rpc-app_version": APP_VERSION,
        "x-rpc-channel": "miyousheluodi",
        "x-rpc-client_type": CLIENT_TYPE,
        "x-rpc-device_id": device_id,
    }


<<<<<<< HEAD
def http_request(method: str, url: str, headers: dict, data: bytes = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
    except Exception as e:
=======
def http_request(method, url, headers, data=None, timeout=20):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d
        return {"retcode": -1, "message": f"网络请求异常: {e}"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"retcode": -2, "message": f"响应非 JSON: {raw[:200]}"}


<<<<<<< HEAD
def describe(retcode, message: str) -> str:
    if retcode == 0:
        return "OK"
    hint = ERRCODE_DESC.get(retcode)
    base = f"retcode={retcode} {message}"
    return base + (f"（{hint}）" if hint and str(retcode) not in str(message) else "")


# ============ 核心业务 ============

def get_user_roles(cookie: str, device_id: str) -> list:
    """一次性拉取账号下全部绑定角色"""
    headers = base_headers(cookie, device_id)
    headers["Referer"] = "https://webstatic.mihoyo.com/"
    headers["DS"] = get_ds()
    out = http_request("GET", BINDING_API, headers)
    if out.get("retcode") != 0:
        print(f"获取角色列表失败: {describe(out.get('retcode'), out.get('message', ''))}")
        return []
    return out.get("data", {}).get("list", [])


def sign_role(cookie: str, device_id: str, game_biz: str, role: dict) -> dict:
    """对单个角色执行签到"""
    game = GAME_CONFIG[game_biz]
    act_id = game["act_id"]
    uid = role.get("game_uid", 0)
    region = role.get("region", "")

    url = game["host"] + game["path"] + "/sign"
    body = json.dumps({"act_id": act_id, "region": region, "uid": uid},
                      separators=(",", ":"))

    headers = base_headers(cookie, device_id)
    headers.update({
        "Content-Type": "application/json",
        "Referer": REFERER,
        "Origin": ORIGIN,
        "x-rpc-act_id": act_id,
        "DS": get_ds(),
    })
    if game.get("signgame"):
        headers["x-rpc-signgame"] = game["signgame"]

    out = http_request("POST", url, headers, data=body.encode("utf-8"))
    retcode = out.get("retcode")
    message = out.get("message", "")

    if retcode == 0:
        rewards = (out.get("data") or {}).get("rewards") or []
        reward_str = ", ".join(f"{r.get('name', '')}x{r.get('cnt', 0)}" for r in rewards) \
            if rewards else "接口未返回奖励明细"
        return {"status": "OK", "message": f"签到成功: {reward_str}"}
    if retcode == -5003:
        return {"status": "SKIP", "message": "今日已签到"}
    return {"status": "FAIL", "message": f"签到失败({describe(retcode, message)})"}


def main():
    print("=" * 52)
    print("米游社每日签到")
    print("=" * 52)

    config = load_config()
    cookie = (config.get("cookie") or "").strip()

    if not cookie or cookie == "在此填入你的米游社Cookie":
        print("错误：config.json 中 cookie 字段为空")
        print("请先编辑 config.json，填入你的米游社网页端 Cookie")
        sys.exit(1)

    device_id = (config.get("device_id") or "").strip() or device_id_from_cookie(cookie)
    overrides = config.get("act_id_overrides", {}) or {}

    print("\n[1/3] 获取账号绑定角色...")
    roles = get_user_roles(cookie, device_id)
    if not roles:
        print("未获取到任何角色，请检查 Cookie 是否有效")
        sys.exit(1)

    print(f"共获取到 {len(roles)} 个绑定角色:")
    for r in roles:
        print(f"  - {r.get('game_biz')}: {r.get('nickname')} "
              f"(UID: {r.get('game_uid')}, 区服: {r.get('region')}, 等级: {r.get('level')})")

    print("\n[2/3] 开始执行签到...")
    results = []
    for role in roles:
        biz = role.get("game_biz", "")
        game = GAME_CONFIG.get(biz)
        game_name = game["name"] if game else biz
        nickname = role.get("nickname", "未知")
        uid = role.get("game_uid", "未知")

        if not game:
            print(f"\n  [{game_name}] {nickname} (UID: {uid})")
            print("    -> SKIP: 不支持的游戏类型")
            continue

        # 允许通过配置覆盖 act_id
        if overrides.get(biz):
            game = dict(game, act_id=overrides[biz].strip())
            GAME_CONFIG[biz] = game

        print(f"\n  [{game_name}] {nickname} (UID: {uid})")
        res = sign_role(cookie, device_id, biz, role)
        print(f"    -> {res['status']}: {res['message']}")
        results.append({
            "game": game_name, "nickname": nickname, "uid": uid,
            "status": res["status"], "message": res["message"],
        })

    print("\n" + "=" * 52)
    print("[3/3] 签到结果汇总")
    print("=" * 52)
    print("---SUMMARY---")

    ok_count = sum(1 for r in results if r["status"] == "OK")
    skip_count = sum(1 for r in results if r["status"] == "SKIP")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    prefix_map = {"OK": "OK  |", "SKIP": "SKIP|", "FAIL": "FAIL|"}
    for r in results:
        print(f"{prefix_map.get(r['status'], '????|')} "
              f"[{r['game']}] {r['nickname']} (UID:{r['uid']}) - {r['message']}")

    print("-" * 52)
    print(f"总计: {len(results)} 个角色 | 成功: {ok_count} | 已签到: {skip_count} | 失败: {fail_count}")
    print("---END---")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
=======
def get_game_roles(cookie, device_id, game_biz):
    """拉取该账号下绑定了某游戏的角色列表。"""
    url = (
        "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie"
        f"?game_biz={game_biz}"
    )
    headers = _base_headers(cookie, device_id)
    headers["Referer"] = "https://webstatic.mihoyo.com/"
    headers["DS"] = get_ds()
    resp = http_request("GET", url, headers)
    if resp.get("retcode") != 0:
        return None, resp.get("message") or "未知错误"
    return resp.get("data", {}).get("list", []), None


def is_signed_today(cookie, device_id, game, region, uid):
    """查询今天是否已签到（/event/luna/info）。返回值：True/False/None（查询失败）。"""
    url = (
        "https://api-takumi.mihoyo.com/event/luna/info"
        f"?lang=zh-cn&act_id={game['act_id']}&region={region}&uid={uid}"
    )
    headers = _base_headers(cookie, device_id)
    headers["Referer"] = REFERER
    headers["Origin"] = ORIGIN
    headers["DS"] = get_ds()
    if game.get("signgame"):
        headers["x-rpc-signgame"] = game["signgame"]
    resp = http_request("GET", url, headers)
    if resp.get("retcode") != 0:
        return None, resp.get("message")
    data = resp.get("data", {})
    return data.get("is_sign", False), None


def sign(cookie, device_id, game):
    """对单个游戏下的所有角色执行签到。返回结果文本列表。"""
    lines = []
    roles, err = get_game_roles(cookie, device_id, game["game_biz"])
    if err is not None:
        return [f"{game['name']}: 获取角色失败 - {err}"]
    if not roles:
        return [f"{game['name']}: 未绑定游戏角色（请确认账号已绑定 {game['name']}）"]

    for role in roles:
        region = role.get("region")
        uid = role.get("game_uid")
        nickname = role.get("nickname") or uid

        # 先查今天是否已签
        signed, info_err = is_signed_today(cookie, device_id, game, region, uid)
        if signed is True:
            lines.append(f"SKIP| {game['name']} | {nickname} (uid={uid}) 今天已经签到过")
            continue

        url = "https://api-takumi.mihoyo.com/event/luna/sign"
        body = json.dumps(
            {"act_id": game["act_id"], "region": region, "uid": uid},
            separators=(",", ":"),
        )
        headers = _base_headers(cookie, device_id)
        headers.update({
            "Content-Type": "application/json",
            "Referer": REFERER,
            "Origin": ORIGIN,
            "x-rpc-act_id": game["act_id"],
            "DS": get_ds(),
        })
        if game.get("signgame"):
            headers["x-rpc-signgame"] = game["signgame"]

        resp = http_request("POST", url, headers, data=body.encode("utf-8"))
        rc = resp.get("retcode")
        msg = resp.get("message")
        if rc == 0:
            lines.append(f"OK  | {game['name']} | {nickname} (uid={uid}) 签到成功")
        elif rc == -5003:
            lines.append(f"SKIP| {game['name']} | {nickname} (uid={uid}) 今天已经签到过")
        else:
            lines.append(
                f"FAIL| {game['name']} | {nickname} (uid={uid}) "
                f"retcode={rc} message={msg}"
            )
    return lines


def main():
    cookie, device_id = load_config()
    all_lines = []
    for key, g in GAMES.items():
        print(f"\n=== {g['name']} ===")
        res = sign(cookie, device_id, g)
        for line in res:
            print("  " + line)
            all_lines.append(line)

    print("\n---SUMMARY---")
    for line in all_lines:
        print(line)
    failed = [l for l in all_lines if l.startswith("FAIL")]
    return all_lines, failed


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}")
        sys.exit(1)
>>>>>>> 7196630bfc691681457679fecd8011c0142b537d
