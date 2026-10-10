#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
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
"""

import json
import time
import random
import string
import hashlib
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

        "Accept-Language": "zh-CN,en-US;q=0.8",
        "Cookie": cookie,
        "User-Agent": USER_AGENT,
        "X-Requested-With": "com.mihoyo.hyperion",
        "x-rpc-app_version": APP_VERSION,
        "x-rpc-channel": "miyousheluodi",
        "x-rpc-client_type": CLIENT_TYPE,
        "x-rpc-device_id": device_id,
    }


def http_request(method: str, url: str, headers: dict, data: bytes = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
    except Exception as e:

        return {"retcode": -1, "message": f"网络请求异常: {e}"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"retcode": -2, "message": f"响应非 JSON: {raw[:200]}"}

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

