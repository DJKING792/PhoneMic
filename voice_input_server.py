#!/usr/bin/env python3
"""
TypMic 服务端（云端 MiMo ASR API + aiohttp）
手机录音 -> HTTPS POST 音频 -> 调用小米 MiMo-V2.5-ASR 云端识别 -> 粘贴到光标 + 返回结果

设计要点：
- 监听 0.0.0.0，局域网内任意手机均可作为麦克风（按需求，不加鉴权）。
- 首次运行自动生成自签根 CA + 服务端证书（SAN 含局域网 IP / localhost），
  以便手机用 HTTPS 访问（getUserMedia 需要安全上下文）。
- 识别走云端 MiMo API（OpenAI 兼容），无需本地下载模型；
  需在环境变量 MIMO_API_KEY 中配置小米 MiMo API key（https://platform.xiaomimimo.com）。
- 可选【离线模式】：设置 TYPOMIC_ASR=local 后改用本地 faster-whisper 识别，
  语音不出本机，无需任何 API key（需 pip install faster-whisper，首次会下载模型）。
- 接口处理中，ffmpeg 转换放到线程，API 请求异步进行，避免卡住事件循环；
  粘贴动作放进 executor，并放慢剪贴板还原节奏，避免粘到旧内容。
"""

import asyncio
import base64
import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import aiohttp
    from aiohttp import web
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import pyautogui
    import pyperclip
except ImportError as _e:
    sys.stderr.write(
        "\n[启动失败] 缺少必要依赖：%s\n\n"
        "请先安装依赖再运行：\n"
        "  python -m venv .venv\n"
        "  .venv\\Scripts\\activate\n"
        "  pip install -r requirements.txt\n\n"
        "或直接双击 start.bat 自动完成以上步骤。\n" % _e
    )
    sys.exit(1)

pyautogui.FAILSAFE = False

# 本地离线识别后端（faster-whisper），仅离线模式按需启用；核心依赖不受影响。
from local_asr import LocalWhisperASR
# 文本后处理：术语表修正 + 可选 AI 润色（失败一律降级为原文，不阻断粘贴）。
from text_polish import Polisher, load_glossary, apply_glossary

ROOT = Path(__file__).parent
TEMP_DIR = ROOT / "audio_temp"
TEMP_DIR.mkdir(exist_ok=True)
GLOSSARY_FILE = ROOT / "glossary.txt"

CERT_FILE = ROOT / "cert.pem"
KEY_FILE = ROOT / "key.pem"
CA_CERT_FILE = ROOT / "rootCA.pem"
CA_KEY_FILE = ROOT / "rootCA-key.pem"

def load_dotenv(path=None):
    """从同目录 .env 读取键值到环境变量（不覆盖已存在的环境变量）。

    这样无需每次手动 set MIMO_API_KEY，把 key 写进项目根目录的 .env 即可：
        MIMO_API_KEY=你的key
    """
    p = Path(path) if path else (ROOT / ".env")
    if not p.exists():
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


# 云端识别使用小米 MiMo ASR API，需在环境变量 MIMO_API_KEY 中配置 API key。
# 优先取系统环境变量；若没有，则从同目录 .env 读取。
# 前往 https://platform.xiaomimimo.com 申请。
load_dotenv()
MIMO_API_KEY = os.environ.get("MIMO_API_KEY", "").strip()

# 识别模式：cloud（默认，走小米 MiMo 云端）或 local（本地 faster-whisper 离线）
ASR_MODE = os.environ.get("TYPOMIC_ASR", "cloud").strip().lower()
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small").strip() or "small"

# --------------------------------------------------------------------------- #
# AI 润色 / 术语表（文本后处理，可选增益，默认关闭）
# --------------------------------------------------------------------------- #
# 润色开关：on 才启用；其余均自带合理默认，关掉即退回纯识别。
POLISH_ON = os.environ.get("TYPOMIC_POLISH", "off").strip().lower() == "on"
# 润色接口（OpenAI 兼容 chat/completions），默认复用小米 MiMo 的对话端点。
POLISH_URL = os.environ.get(
    "TYPOMIC_POLISH_URL", "https://api.xiaomimimo.com/v1/chat/completions"
).strip()
# 润色模型名（需为支持 chat 的模型）；默认 mimo-v2.5-flash，按你的账号可改。
POLISH_MODEL = os.environ.get("TYPOMIC_POLISH_MODEL", "mimo-v2.5-flash").strip()
# 润色 API key：默认复用 MIMO_API_KEY，也可单独配置。
POLISH_API_KEY = os.environ.get("TYPOMIC_POLISH_API_KEY", MIMO_API_KEY).strip()
# 润色模式：full（默认，去口语+顺句+分段+标点）或 punctuate（只补标点不改写）。
POLISH_MODE = os.environ.get("TYPOMIC_POLISH_MODE", "full").strip().lower()

polisher = Polisher(POLISH_URL, POLISH_API_KEY, POLISH_MODEL, timeout=30, mode=POLISH_MODE)
# 术语表开关：默认 on（有 glossary.txt 即生效）；设 TYPOMIC_GLOSSARY=off 可关闭。
GLOSSARY_ENABLED = os.environ.get("TYPOMIC_GLOSSARY", "on").strip().lower() == "on"
# 术语表：dict 形式；关闭或文件不存在则为空（不生效）。
GLOSSARY_REPLACEMENTS, GLOSSARY_TERMS = (
    load_glossary(GLOSSARY_FILE) if GLOSSARY_ENABLED else ({}, set())
)

asr = None  # 懒加载，避免启动即占内存
routes = web.RouteTableDef()

# --------------------------------------------------------------------------- #
# 启动诊断 / 连接日志（用于排查“手机连不上”类问题）
# --------------------------------------------------------------------------- #
START_TIME = time.time()

# 最近的连接记录（供 /api/status 展示，最多保留 50 条）
CONNECTION_LOG: list = []

# --------------------------------------------------------------------------- #
# 透明流水线：SSE 事件流（识别中/润色中/已粘贴）+ 今日用量统计
# --------------------------------------------------------------------------- #
# 订阅 SSE 的客户端队列集合；每个桌面端页面一个队列。
PIPELINE_CLIENTS: set = set()
# 今日统计：次数 / 字数 / 识别耗时累计 / 润色耗时累计（跨午夜自动归零）
STATS = {"date": "", "count": 0, "chars": 0, "asr_ms": 0.0, "polish_ms": 0.0}


def broadcast(event: dict):
    """向所有订阅 SSE 的桌面端推送一个流水线事件。非阻塞、单点失败不影响主链路。"""
    dead = []
    for q in PIPELINE_CLIENTS:
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        PIPELINE_CLIENTS.discard(q)


def record_stats(chars: int, asr_ms: float, polish_ms: float):
    """累加一次成功识别的用量统计；跨日自动重置。"""
    today = time.strftime("%Y-%m-%d")
    if STATS["date"] != today:
        STATS.update(date=today, count=0, chars=0, asr_ms=0.0, polish_ms=0.0)
    STATS["count"] += 1
    STATS["chars"] += chars
    STATS["asr_ms"] += asr_ms
    STATS["polish_ms"] += polish_ms


def stats_snapshot():
    """返回给前端的统计数据（平均延迟按次数折算）。"""
    n = STATS["count"] or 1
    return {
        "date": STATS["date"],
        "count": STATS["count"],
        "chars": STATS["chars"],
        "avg_asr_ms": round(STATS["asr_ms"] / n),
        "avg_polish_ms": round(STATS["polish_ms"] / n),
    }


def record_connection(remote, method, path, status, ua):
    """记录一次请求，帮助排查手机是否真正到达了服务端。"""
    skip = {"/api/status", "/desktop/qr.png", "/api/info", "/favicon.ico"}
    if path in skip:
        return
    CONNECTION_LOG.append({
        "time": time.strftime("%H:%M:%S"),
        "ip": remote or "?",
        "method": method,
        "path": path,
        "status": status,
        "ua": (ua or "")[:50],
    })
    while len(CONNECTION_LOG) > 50:
        CONNECTION_LOG.pop(0)


def get_all_local_ips():
    """返回本机所有非回环 IPv4，用于提示用户哪个是局域网地址。"""
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip and ip != "127.0.0.1":
                ips.add(ip)
    except Exception:
        pass
    out = get_wifi_ip()
    if out != "127.0.0.1":
        ips.add(out)
    return sorted(ips)


def ffmpeg_available():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def port_in_use(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


@web.middleware
async def log_requests(request, handler):
    remote = request.remote
    ua = request.headers.get("User-Agent", "")
    try:
        resp = await handler(request)
        record_connection(remote, request.method, request.path, resp.status, ua)
        return resp
    except Exception:
        record_connection(remote, request.method, request.path, 500, ua)
        raise


# --------------------------------------------------------------------------- #
# 网络 / 证书
# --------------------------------------------------------------------------- #
def get_wifi_ip() -> str:
    """返回本机当前用于出网的私网 IPv4 地址（用于证书 SAN 与展示）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    try:
        if ipaddress.ip_address(ip).is_private:
            return ip
    except ValueError:
        pass
    return "127.0.0.1"


def _build_ca():
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "VoiceInput Root CA")]
    )
    now = datetime.now(timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=398))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return ca_key, ca_cert


def _build_server_cert(ca_key, ca_cert, ip: str):
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    san = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address(ip)),
    ])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "VoiceInput")]))
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=397))
        .add_extension(san, critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return server_key, server_cert


def ensure_certs() -> None:
    if CERT_FILE.exists() and KEY_FILE.exists() and CA_CERT_FILE.exists():
        return
    print("[证书] 未找到证书，正在生成自签根 CA + 服务端证书 ...", flush=True)
    ip = get_wifi_ip()
    ca_key, ca_cert = _build_ca()
    server_key, server_cert = _build_server_cert(ca_key, ca_cert, ip)

    CA_KEY_FILE.write_bytes(ca_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    CA_CERT_FILE.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    KEY_FILE.write_bytes(server_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    CERT_FILE.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    print("[证书] 生成完成。", flush=True)


# --------------------------------------------------------------------------- #
# 语音识别
# --------------------------------------------------------------------------- #
class MimoASR:
    """小米 MiMo-V2.5-ASR 云端语音识别（OpenAI 兼容接口）。

    需在环境变量 MIMO_API_KEY 中配置小米 MiMo API key
    （前往 https://platform.xiaomimimo.com 申请）。
    """

    API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
    MODEL = "mimo-v2.5-asr"

    def __init__(self):
        self.api_key = MIMO_API_KEY

    def ready(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, wav_path: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "未配置 MIMO_API_KEY。请在环境变量中设置小米 MiMo API key"
                "（前往 https://platform.xiaomimimo.com 申请），然后重启服务。"
            )
        # 读取音频并 base64（小米接口接收 data URI 形式的音频）
        with open(wav_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("ascii")

        payload = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/wav;base64,{audio_b64}"
                            },
                        }
                    ],
                }
            ],
            "asr_options": {"language": "auto"},
        }
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.API_URL, json=payload, headers=headers, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"MiMo API 返回 {resp.status}: {body[:400]}")
                data = await resp.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(
                f"MiMo API 响应解析失败: {json.dumps(data, ensure_ascii=False)[:400]}"
            )
        return (text or "").strip()


def convert_to_wav(input_path: str, output_dir: str) -> str:
    """用 ffmpeg 把上传的音频转为 16k 单声道 wav。失败抛出明确错误。"""
    output_path = str(Path(output_dir) / f"audio_{int(time.time() * 1000)}.wav")
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", input_path,
         "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", output_path],
        capture_output=True, timeout=30,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="ignore")[-500:]
        raise RuntimeError(f"ffmpeg 退出码 {proc.returncode}: {err}")
    if not Path(output_path).exists():
        raise RuntimeError("ffmpeg 未生成输出文件")
    return output_path


def prune_temp(keep: int = 20) -> None:
    """只保留最近 keep 个临时文件，避免长期运行堆积。"""
    files = [p for p in TEMP_DIR.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[keep:]:
        try:
            p.unlink()
        except OSError:
            pass


def paste_text(text: str) -> None:
    """把文本复制到剪贴板并 ctrl+v 粘贴到当前光标。在线程中执行。"""
    try:
        old = pyperclip.paste()
    except Exception:
        old = ""
    pyperclip.copy(text)
    time.sleep(0.3)            # 等复制生效
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.4)            # 等粘贴完成再还原剪贴板
    try:
        pyperclip.copy(old)
    except Exception:
        pass
    print(f"[识别+粘贴] {text}", flush=True)


def send_key_action(action: str) -> None:
    """把手机端「回车/换行/删除/清空」指令映射成真实按键事件。

    与语音流程完全解耦：打字或语音都行，对光标处任意输入都生效；
    发的是标准按键事件，Windows / Mac / Linux 都能识别（无需 AutoHotkey 这类
    Windows 专属脚本）。实现极轻——手机端只是多发一条控制消息。
    """
    try:
        if action == "enter":
            # 回车：确认 / 发送
            pyautogui.press("enter")
        elif action == "newline":
            # 换行：Shift+Enter 在大多数软件里只换行不发送（微信 / 聊天框等）
            pyautogui.hotkey("shift", "enter")
        elif action == "backspace":
            # 删除：退格一格
            pyautogui.press("backspace")
        elif action == "clear":
            # 清空：全选 + 删除（macOS 用 Cmd+A，其它用 Ctrl+A）
            mod = "command" if sys.platform == "darwin" else "ctrl"
            pyautogui.hotkey(mod, "a")
            pyautogui.press("backspace")
        else:
            return
        print(f"[按键控制] {action}", flush=True)
    except Exception as e:
        print(f"[按键控制] 失败 {action}: {e}", flush=True)


# --------------------------------------------------------------------------- #
# HTTP 接口
# --------------------------------------------------------------------------- #
@routes.get("/")
async def index(request):
    return web.FileResponse(ROOT / "index.html")


@routes.get("/desktop")
async def desktop(request):
    # 电脑端扫码页：显示访问地址二维码，手机扫一扫直接打开
    return web.FileResponse(ROOT / "desktop.html")


@routes.get("/desktop/qr.png")
async def desktop_qr(request):
    # 实时生成访问地址的二维码图片（依赖 qrcode + Pillow）
    try:
        import io
        import qrcode
    except ImportError:
        return web.Response(status=500, text="缺少依赖，请先 pip install 'qrcode[pil]'")
    ip = get_wifi_ip()
    url = f"https://{ip}:8443"
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return web.Response(body=buf.getvalue(), content_type="image/png")


@routes.get("/api/info")
async def api_info(request):
    # 供电脑端页面获取真实访问地址（局域网 IP）
    return web.json_response({"url": f"https://{get_wifi_ip()}:8443"})


@routes.get("/api/ping")
async def api_ping(request):
    # 手机/浏览器用来自检是否真正连到了本服务；返回的 your_ip
    # 能让用户在电脑端确认“手机确实到达了服务端”。
    return web.json_response({
        "ok": True,
        "your_ip": request.remote or "?",
        "server": f"https://{get_wifi_ip()}:8443",
    })


@routes.get("/api/status")
async def api_status(request):
    # 电脑端实时状态：服务是否正常、依赖是否就绪、最近有哪些连接。
    return web.json_response({
        "running": True,
        "lan_ip": get_wifi_ip(),
        "port": 8443,
        "server_url": f"https://{get_wifi_ip()}:8443",
        "ffmpeg_ok": ffmpeg_available(),
        "cert_ok": CERT_FILE.exists() and KEY_FILE.exists() and CA_CERT_FILE.exists(),
        "mode": "local-whisper" if ASR_MODE == "local" else "cloud-mimo",
        "asr_mode": ASR_MODE,
        "mimo_api_key_set": bool(MIMO_API_KEY),
        "polish_enabled": POLISH_ON,
        "polish_ready": polisher.ready(),
        "polish_mode": POLISH_MODE,
        "glossary_count": len(GLOSSARY_REPLACEMENTS),
        "uptime_sec": int(time.time() - START_TIME),
        "stats": stats_snapshot(),
        "connections": CONNECTION_LOG[-30:],
    })


@routes.get("/api/stream")
async def api_stream(request):
    """SSE 事件流：实时推送识别流水线阶段（识别中/润色中/已粘贴）+ 今日统计。
    供电脑端桌面页展示透明进度条。客户端断开即清理。"""
    resp = web.StreamResponse(headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
    await resp.prepare(request)
    q = asyncio.Queue()
    PIPELINE_CLIENTS.add(q)
    # 初始事件：当前统计快照，让页面一连接就有数据
    try:
        await resp.write(("data: " + json.dumps(
            {"stage": "idle", "stats": stats_snapshot()}, ensure_ascii=False) + "\n\n").encode("utf-8"))
        while True:
            event = await q.get()
            payload = "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
            await resp.write(payload.encode("utf-8"))
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        PIPELINE_CLIENTS.discard(q)
    return resp


@routes.post("/api/transcribe")
async def transcribe_api(request):
    global asr
    reader = await request.multipart()
    field = await reader.next()
    if field is None:
        return web.json_response({"ok": False, "error": "未收到音频"})

    webm_path = str(TEMP_DIR / f"input_{int(time.time() * 1000)}.webm")
    with open(webm_path, "wb") as f:
        while True:
            chunk = await field.read_chunk(65536)
            if not chunk:
                break
            f.write(chunk)

    # ffmpeg 转换（线程中，避免阻塞事件循环）
    try:
        wav_path = await asyncio.to_thread(convert_to_wav, webm_path, str(TEMP_DIR))
    except Exception as e:
        print(f"[ffmpeg] {e}", flush=True)
        return web.json_response({"ok": False, "error": f"音频转换失败: {e}"})

    if asr is None:
        asr = LocalWhisperASR(WHISPER_MODEL) if ASR_MODE == "local" else MimoASR()
    # 调用识别（云端 MiMo 或本地 faster-whisper；异步，不阻塞事件循环）
    broadcast({"stage": "asr", "ts": int(time.time() * 1000)})
    try:
        t0 = time.time()
        text = await asr.transcribe(wav_path)
        asr_ms = (time.time() - t0) * 1000
    except Exception as e:
        tag = "Local" if ASR_MODE == "local" else "MiMo"
        print(f"[{tag}] {e}", flush=True)
        broadcast({"stage": "error", "msg": f"识别失败: {e}"})
        return web.json_response({"ok": False, "error": f"识别失败: {e}"})

    if not text.strip():
        broadcast({"stage": "done", "text": "(未识别到语音)", "ms": round(asr_ms)})
        return web.json_response({"ok": True, "text": "(未识别到语音)"})

    # —— 文本后处理：术语表修正 + 可选 AI 润色（任一环节失败都降级为原文）——
    if GLOSSARY_ENABLED:
        text = apply_glossary(text, GLOSSARY_REPLACEMENTS)
    polish_ms = 0.0
    if POLISH_ON:
        broadcast({"stage": "polish", "ts": int(time.time() * 1000)})
        t1 = time.time()
        text = await polisher.polish(text, GLOSSARY_TERMS)
        polish_ms = (time.time() - t1) * 1000
        if GLOSSARY_ENABLED:
            text = apply_glossary(text, GLOSSARY_REPLACEMENTS)  # 润色后再保一道术语
        broadcast({"stage": "polish_done", "ms": round(polish_ms)})

    # 粘贴放在 executor，并等它完成再返回，保证时序
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, paste_text, text)

    broadcast({"stage": "done", "text": text, "ms": round(asr_ms),
               "polish_ms": round(polish_ms), "chars": len(text),
               "stats": stats_snapshot()})
    record_stats(len(text), asr_ms, polish_ms)

    # 清理临时文件
    try:
        Path(webm_path).unlink(missing_ok=True)
        Path(wav_path).unlink(missing_ok=True)
    except OSError:
        pass
    prune_temp()

    return web.json_response({"ok": True, "text": text})


@routes.post("/api/control")
async def control_api(request):
    # 手机端「回车 / 换行 / 删除 / 清空」四个按钮：发标准按键事件到电脑光标。
    # 与语音流程解耦，对任意输入都生效，且跨平台（Win / Mac / Linux 都认）。
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid JSON"}, status=400)
    action = data.get("action") if isinstance(data, dict) else None
    if action not in ("enter", "newline", "backspace", "clear"):
        return web.json_response({"ok": False, "error": "unknown action"}, status=400)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_key_action, action)
    return web.json_response({"ok": True, "action": action})


# --------------------------------------------------------------------------- #
# 启动
# --------------------------------------------------------------------------- #
def print_startup_diagnostics(ip):
    """启动即打印清晰的诊断信息，让连接问题一目了然。"""
    ffmpeg_ok = ffmpeg_available()
    port_used = port_in_use(8443)
    local_ips = get_all_local_ips()
    cert_ok = CERT_FILE.exists() and KEY_FILE.exists() and CA_CERT_FILE.exists()
    line = "=" * 60
    print(line)
    print("TypMic - 启动诊断")
    print(line)
    print(f"本机局域网 IP : {ip}")
    print(f"手机访问地址  : https://{ip}:8443")
    print(f"电脑扫码页    : https://localhost:8443/desktop")
    print(f"ffmpeg 可用   : {'是' if ffmpeg_ok else '否（音频转换会失败，请安装 ffmpeg 并加入 PATH）'}")
    print(f"证书状态      : {'已生成' if cert_ok else '将自动生成'}")
    print(f"端口 8443     : {'已被占用！' if port_used else '空闲，可正常监听'}")
    if ASR_MODE == "local":
        try:
            import faster_whisper  # noqa: F401
            fw_ok = True
        except Exception:
            fw_ok = False
        print(f"识别模式      : 本地 faster-whisper 离线（模型={WHISPER_MODEL}，无需 API key）")
        print(f"faster-whisper: {'已安装 ✔' if fw_ok else '未安装！离线模式需先 pip install faster-whisper'}")
        if not fw_ok:
            RED = "\033[91m"
            RESET = "\033[0m"
            bar = "!" * 62
            print(RED + bar + RESET)
            print(RED + "!!! 离线模式已开启，但缺少 faster-whisper !!!" + RESET)
            print(RED + "!!! 请安装： pip install faster-whisper" + RESET)
            print(RED + bar + RESET)
    else:
        print(f"识别模式      : 云端 MiMo-V2.5-ASR（小米 API，OpenAI 兼容）")
        if MIMO_API_KEY:
            print(f"MIMO_API_KEY  : 已配置 ✔")
        else:
            RED = "\033[91m"
            RESET = "\033[0m"
            bar = "!" * 62
            print(RED + bar + RESET)
            print(RED + "!!! MIMO_API_KEY 未配置，语音识别将无法工作 !!!" + RESET)
            print(RED + "!!! 请设置后重启服务：" + RESET)
            print(RED + "        set MIMO_API_KEY=你的key" + RESET)
            print(RED + "    或把 key 写入项目根目录 .env 文件（一行即可）：" + RESET)
            print(RED + "        MIMO_API_KEY=你的key" + RESET)
            print(RED + "    申请地址：https://platform.xiaomimimo.com" + RESET)
            print(RED + bar + RESET)
    if local_ips:
        print("本机所有 IPv4 : " + ", ".join(local_ips))
    # 文本后处理状态
    if POLISH_ON:
        if polisher.ready():
            mode_cn = "只加标点" if POLISH_MODE == "punctuate" else "全量润色"
            print(f"AI 润色        : 已开启 ✔（模式={mode_cn}，模型={POLISH_MODEL}）")
        else:
            YEL = "\033[93m"
            RESET = "\033[0m"
            print(YEL + "!!! AI 润色已开启，但接口/key/模型未就绪，将自动降级为不润色 !!!" + RESET)
            print(YEL + "    请检查 TYPOMIC_POLISH_URL / TYPOMIC_POLISH_API_KEY / TYPOMIC_POLISH_MODEL" + RESET)
    else:
        print(f"AI 润色        : 关闭（设 TYPOMIC_POLISH=on 可开启；默认纯识别）")
    if GLOSSARY_ENABLED:
        print(f"术语表        : 已加载 {len(GLOSSARY_REPLACEMENTS)} 条规则"
              + ("" if GLOSSARY_REPLACEMENTS else "（无 glossary.txt，可建一个做错词纠正）"))
    else:
        print("术语表        : 关闭（设 TYPOMIC_GLOSSARY=on 可开启，默认开启）")
    print("-" * 60)
    if not ffmpeg_ok:
        print("⚠ 警告：未检测到 ffmpeg，手机录音将无法转为文字。")
        print("  请到 https://ffmpeg.org 下载并加入系统 PATH。")
    if port_used:
        print("⚠ 警告：端口 8443 已被占用，手机可能连不上或启动失败。")
        print("  请关闭占用该端口的程序，或修改本文件端口后重启。")
    print("手机连不上时，按此排查：")
    print("  1. 手机和电脑必须在【同一个 WiFi】（不能用手机流量）。")
    print("  2. 安卓首次打开会提示证书风险，点『高级』->『继续』即可。")
    print("     iPhone 无法下载证书/点继续：须先把电脑端的 rootCA.pem")
    print("     用 AirDrop / 邮件 / 微信文件传到 iPhone 安装并开启完全信任，再打开页面。")
    print("  3. 若提示『已拒绝连接 / ERR_CONNECTION_REFUSED』：多为 Windows")
    print("     防火墙拦截，请允许 python 入站，或放行 8443 端口。")
    print("  4. 电脑端打开 https://localhost:8443/desktop 可看实时连接状态。")
    print(line)


async def main():
    ensure_certs()
    app = web.Application(middlewares=[log_requests])
    app.add_routes(routes)

    ip = get_wifi_ip()
    print_startup_diagnostics(ip)

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(str(CERT_FILE), str(KEY_FILE))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8443, ssl_context=ssl_ctx)
    try:
        await site.start()
    except OSError as e:
        print("\n" + "!" * 60)
        print("启动失败：无法监听端口 8443")
        print(f"错误信息：{e}")
        print("可能原因：")
        print("  1. 已有另一个服务实例在运行（端口被占用）")
        print("  2. 其他程序（如另一个 Python/服务）占用了 8443")
        print("解决办法：")
        print("  - 关闭其他实例/程序后重试，或")
        print("  - 修改本文件中的端口 (8443) 后重启")
        print("!" * 60)
        return

    print("服务已启动，保持此窗口打开。按 Ctrl+C 停止。\n")

    # 控制台也打印一个 ASCII 二维码，方便直接扫
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(f"https://{ip}:8443")
        qr.print_ascii()
    except Exception:
        pass

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已停止服务")
