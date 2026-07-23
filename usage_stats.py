#!/usr/bin/env python3
"""TypMic 真实用量统计 —— 持久化累计，纯标准库，不依赖任何第三方包。

数据存本地 ``usage_stats.json``（本地数据，**绝不进发布包、绝不推 GitHub**）。
记录的都是作者自己真实使用的反馈：
  - total_count : 累计成功识别次数
  - total_chars : 累计输入字符数
  - daily       : 按日明细 {YYYY-MM-DD: {count, chars}}
这些信息用于向访客展示「作者自己天天在用」，增强项目可信度。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATS_PATH = ROOT / "usage_stats.json"

DEFAULT = {
    "total_count": 0,    # 累计成功识别次数
    "total_chars": 0,    # 累计输入字符数
    "total_asr_ms": 0.0, # 累计识别耗时(ms)，用于折算平均速度
    "total_polish_ms": 0.0,  # 累计润色耗时(ms)
    "first_date": "",    # 首次使用日期
    "last_date": "",     # 最近使用日期
    "daily": {},         # { "YYYY-MM-DD": {"count","chars","asr_ms","polish_ms"} }
}


def load_stats() -> dict:
    """读取统计；文件不存在或损坏时回退到 DEFAULT（防止缺字段）。"""
    if STATS_PATH.is_file():
        try:
            data = json.loads(STATS_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    merged = dict(DEFAULT)
    merged.update({k: v for k, v in data.items() if k in DEFAULT})
    return merged


def save_stats(s: dict) -> None:
    STATS_PATH.write_text(
        json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record_usage(chars: int, asr_ms: float = 0.0, polish_ms: float = 0.0) -> dict:
    """记录一次成功识别（真实用量累加），返回最新累计快照。"""
    s = load_stats()
    today = time.strftime("%Y-%m-%d")
    s["total_count"] += 1
    s["total_chars"] += max(0, int(chars))
    s["total_asr_ms"] += max(0.0, float(asr_ms))
    s["total_polish_ms"] += max(0.0, float(polish_ms))
    if not s["first_date"]:
        s["first_date"] = today
    s["last_date"] = today
    day = s["daily"].setdefault(today, {"count": 0, "chars": 0, "asr_ms": 0.0, "polish_ms": 0.0})
    day["count"] += 1
    day["chars"] += max(0, int(chars))
    day["asr_ms"] += max(0.0, float(asr_ms))
    day["polish_ms"] += max(0.0, float(polish_ms))
    save_stats(s)
    return snapshot(s)


def _avg(ms: float, count: int) -> int:
    return round(ms / count) if count else 0


def snapshot(s: dict | None = None) -> dict:
    """返回给前端 / 脚本的累计数字（含当日与速度均值）。"""
    if s is None:
        s = load_stats()
    today = time.strftime("%Y-%m-%d")
    day = s["daily"].get(today, {"count": 0, "chars": 0, "asr_ms": 0.0, "polish_ms": 0.0})
    return {
        "today_count": day["count"],
        "today_chars": day["chars"],
        "today_asr_ms": _avg(day["asr_ms"], day["count"]),
        "today_polish_ms": _avg(day["polish_ms"], day["count"]),
        "total_count": s["total_count"],
        "total_chars": s["total_chars"],
        "first_date": s["first_date"],
        "last_date": s["last_date"],
        "days": len(s["daily"]),
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(snapshot())
