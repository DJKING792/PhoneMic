#!/usr/bin/env python3
"""TypMic 真实用量 → shields.io badge → GitHub Gist（独立仓库，不污染主仓库）。

本地数据在 usage_stats.json，GitHub 读不到，所以把统计推到一个**独立 Gist**，
README 用 shields.io endpoint badge 实时读它，数字随你真实使用自动更新。

前置（在你自己电脑上配置一次）：
  - 环境变量 GITHUB_TOKEN = 你的 PAT（需 gist 权限；不要写进仓库）
  - 首次运行留空 TYPMC_GIST_ID，脚本创建 Gist 并打印 ID，之后存进环境变量

部署（作者本地，一次）：
  Windows 任务计划每天跑：  python update_usage_badge.py
这样 README 顶部的「使用次数 / 已输入字数」badge 就天天自动变，且主仓库
commit 历史干干净净（Gist 是独立仓库）。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from usage_stats import snapshot  # 复用统计模块

API = "https://api.github.com/gists"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
GIST_ID = os.environ.get("TYPMC_GIST_ID") or os.environ.get("GIST_ID")

COUNT_FILE = "stats_count.json"
CHARS_FILE = "stats_chars.json"


def shield(label: str, message: str, color: str = "blue") -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def build_payload() -> dict:
    s = snapshot()
    count = shield("使用次数", f"{s['total_count']:,}", "blue")
    chars = shield("已输入", f"{s['total_chars']:,} 字", "green")
    return {
        COUNT_FILE: {"content": json.dumps(count, ensure_ascii=False)},
        CHARS_FILE: {"content": json.dumps(chars, ensure_ascii=False)},
    }


def push_gist(payload: dict) -> str | None:
    """推到 Gist；返回 GIST_ID（首次创建时）。失败抛异常。"""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "TypMic-usage-badge",
    }
    if GIST_ID:
        req = urllib.request.Request(
            f"{API}/{GIST_ID}",
            data=json.dumps({"files": payload}).encode("utf-8"),
            headers=headers, method="PATCH",
        )
    else:
        req = urllib.request.Request(
            API,
            data=json.dumps({"public": True, "files": payload}).encode("utf-8"),
            headers=headers, method="POST",
        )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("id")


def main() -> int:
    payload = build_payload()
    # 本地也留一份，便于检查 / 手动上传
    for fn, body in payload.items():
        (ROOT / fn).write_text(body["content"], encoding="utf-8")

    if not TOKEN:
        print("[dry-run] 未设置 GITHUB_TOKEN，仅生成本地 JSON：")
        print("  ", ROOT / COUNT_FILE)
        print("  ", ROOT / CHARS_FILE)
        print("配置 PAT 后重新运行即可推送到 Gist。")
        return 0

    try:
        gid = push_gist(payload)
    except urllib.error.URLError as e:
        print(f"[错误] 推送 Gist 失败：{e}")
        return 1
    if gid and not GIST_ID:
        print(f"[完成] 已创建 Gist，ID = {gid}")
        print("请把下面这行加进你的环境变量（用户变量，永久生效）：")
        print(f"  TYPMC_GIST_ID={gid}")
        print("README badge URL 示例：")
        print(f"  https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/DJKING792/{gid}/raw/{COUNT_FILE}")
    else:
        print(f"[完成] 已更新 Gist：{GIST_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
