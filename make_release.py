#!/usr/bin/env python3
"""TypMic 发布打包脚本 —— 生成干净的 Release 压缩包。

只把「运行必需 + 文档 + 静态资源」打进 zip，
绝不包含 .venv / __pycache__ / audio_temp / .env / 证书私钥 / .git 等。

用法：
    python make_release.py            # 版本号取最新 git tag，没有则用日期
    python make_release.py v1.2.0     # 手动指定版本号
产物：
    dist/TypMic-<版本>.zip          # 解压后顶层是 TypMic/ 文件夹
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
TOP = "TypMic"  # zip 内顶层文件夹名

# —— 白名单：单个文件（只装「终端用户跑程序」真正需要的）——
# 刻意不含：README / CONNECT_PHONE 等文档（下载者在 GitHub 页面看即可，包里不塞）、
#          社区/贡献者文档(CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/SUPPORT)、
#          assets/ 截图、打包脚本、.gitignore、.github/ 等——对下载即用者无作用。
FILES = [
    # 运行必需
    "voice_input_server.py",
    "local_asr.py",
    "text_polish.py",          # 文本后处理：术语表 + AI 润色（被 voice_input_server 依赖）
    "index.html",
    "desktop.html",
    "start.bat",
    "allow_firewall.bat",
    "trust_cert.bat",          # 安装本地根证书到「受信任的根证书颁发机构」，消除浏览器自签警告
    "usage_stats.py",          # 真实用量统计（持久化累计，被 voice_input_server 依赖）
    "update_usage_badge.py",   # 生成 shields badge 并推 Gist（需环境变量 GITHUB_TOKEN）
    "requirements.txt",
    "requirements-whisper.txt",    # 本地 Whisper 引擎依赖（不含 torch，互不牵连）
    "requirements-sensevoice.txt", # 本地 SenseVoice 引擎依赖（含纯 CPU 版 torch）
    ".env.example",
    "glossary.txt.example",    # 术语表样例（复制为 glossary.txt 即可用）
    # 许可证（分发时保留）
    "LICENSE",
]

# —— 白名单：整目录（当前无：assets 仅用于线上 README 展示，不入发布包）——
DIRS: list[str] = []

# —— 黑名单：任何路径命中即拒绝入包（双保险，防止误纳入密钥/垃圾）——
DENY_NAMES = {
    ".venv", "__pycache__", "audio_temp", ".git", "dist", "models",
    ".env", "cert.pem", "key.pem", "rootCA.pem", "rootCA-key.pem",
    "usage_stats.json", "stats_count.json", "stats_chars.json",
}
DENY_SUFFIX = (".log", ".pyc", ".pyo")


def is_denied(rel: str) -> bool:
    if set(Path(rel).parts) & DENY_NAMES:
        return True
    if Path(rel).name in DENY_NAMES:
        return True
    return rel.endswith(DENY_SUFFIX)


def detect_version() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    try:
        v = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if v:
            return v
    except Exception:
        pass
    return date.today().strftime("%Y%m%d")


def collect() -> list[tuple[Path, str]]:
    """返回 [(磁盘绝对路径, zip内相对路径), ...]"""
    items: list[tuple[Path, str]] = []
    for f in FILES:
        p = ROOT / f
        if p.is_file():
            items.append((p, f))
        else:
            print(f"  ! 跳过（不存在）: {f}")
    for d in DIRS:
        base = ROOT / d
        if not base.is_dir():
            print(f"  ! 跳过（目录不存在）: {d}")
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                rel = p.relative_to(ROOT).as_posix()
                if not is_denied(rel):
                    items.append((p, rel))
    return items


def main() -> int:
    version = detect_version()
    items = collect()

    # 安全校验：绝不能有敏感文件
    bad = [rel for _, rel in items if is_denied(rel)]
    if bad:
        print("✗ 安全校验失败，以下敏感文件被误纳入：")
        for b in bad:
            print("   -", b)
        return 1

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{TOP}-{version}.zip"
    if out.exists():
        out.unlink()

    total = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, rel in items:
            z.write(src, f"{TOP}/{rel}")
            total += src.stat().st_size

    print("\n打包完成 ✅")
    print(f"  产物: {out}")
    print(f"  文件数: {len(items)}")
    print(f"  原始体积: {total / 1024 / 1024:.2f} MB")
    print(f"  压缩后: {out.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"  解压后顶层目录: {TOP}/")
    print("\n包含清单：")
    for _, rel in items:
        print("   ", rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
