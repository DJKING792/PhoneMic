"""本地离线语音识别后端（faster-whisper / SenseVoice，二选一）。

可选功能：设置环境变量 TYPOMIC_ASR=whisper 或 =sensevoice 后启用。
- 不需要任何云端 API key，识别完全在本机完成（音频不出本机 / 局域网之外的公网）。
- 首次使用会自动下载对应模型权重（约几百 MB~1GB，仅一次），
  保存到 TypMic/models/ 下以模型名命名的独立文件夹（whisper-small / SenseVoiceSmall 等）。
- 依赖均为【可选】安装，不污染核心依赖：
      pip install faster-whisper        # whisper 引擎
      pip install funasr modelscope      # sensevoice 引擎
"""

import os
import re
import threading
from pathlib import Path

# 模型权重统一下载到 TypMic/models/<模型名> 下，每个模型一个独立文件夹
_MODELS_DIR = Path(__file__).resolve().parent / "models"

_LOCK = threading.Lock()
_MODEL = None

_SV_LOCK = threading.Lock()
_SV_MODEL = None


class LocalWhisperASR:
    """基于 faster-whisper 的离线识别（语音不出本机）。

    默认针对中文场景做了调优，可经环境变量覆盖：
        WHISPER_LANG    识别语种（默认 zh；填 auto 恢复自动检测，en 等其它语种）
        WHISPER_PROMPT  自定义 initial_prompt（默认一句中文引导，提示模型输出简体中文+标点）
        WHISPER_VAD     静音/噪声过滤（默认 on；off 关闭，关闭后长静音段可能干扰识别）
    其余已有：WHISPER_MODEL(默认 small) / WHISPER_DEVICE / WHISPER_COMPUTE。
    """

    def __init__(self, model_size=None):
        self.model_size = (model_size or os.environ.get("WHISPER_MODEL", "small")).strip() or "small"

    def ready(self):
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_model(self):
        global _MODEL
        if _MODEL is None:
            from faster_whisper import WhisperModel

            device = (os.environ.get("WHISPER_DEVICE", "cpu") or "cpu").strip()
            compute_type = (os.environ.get("WHISPER_COMPUTE", "int8") or "int8").strip()
            # 模型保存到 TypMic/models/whisper-<size>（每个模型独立文件夹）
            download_root = _MODELS_DIR / f"whisper-{self.model_size}"
            download_root.mkdir(parents=True, exist_ok=True)
            print(f"[Whisper] 模型目录: {download_root}", flush=True)
            with _LOCK:
                if _MODEL is None:
                    _MODEL = WhisperModel(self.model_size, device=device, compute_type=compute_type,
                                          download_root=str(download_root))
        return _MODEL

    async def transcribe(self, wav_path):
        if not self.ready():
            raise RuntimeError(
                "离线模式需要 faster-whisper。请先安装：\n"
                "  pip install faster-whisper\n"
                "并确认已设置 TYPOMIC_ASR=whisper（本地识别需要该引擎）。"
            )
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_transcribe, wav_path)

    def _sync_transcribe(self, wav_path):
        model = self._get_model()
        # —— 中文场景调优（默认，可经环境变量覆盖）——
        # 1) 强制语种 zh：small 模型在 auto 下极易把中文误判成其它语种导致满屏错字，
        #    强制 zh 是中文准确率提升最大的一步（WHISPER_LANG=auto 可恢复自动检测）。
        lang = (os.environ.get("WHISPER_LANG", "zh") or "zh").strip()
        if lang.lower() == "auto":
            lang = None
        # 2) initial_prompt：引导模型输出简体中文 + 正确标点（WHISPER_PROMPT 可自定义）。
        default_prompt = "以下是中文普通话的语音转写，请输出简体中文并正确使用标点符号。"
        prompt = (os.environ.get("WHISPER_PROMPT", "") or "").strip() or default_prompt
        # 3) VAD 静音过滤：切掉首尾/段间静音与噪声，避免空段与错字（WHISPER_VAD=off 关闭）。
        use_vad = (os.environ.get("WHISPER_VAD", "on") or "on").strip().lower() != "off"
        vad_parameters = None
        if use_vad:
            from faster_whisper import VadOptions
            vad_parameters = VadOptions(
                threshold=0.5,                # 语音/静音判定阈值（Silero 默认）
                min_silence_duration_ms=1000, # 段间静音超过此值才切段，避免短停顿过度切分
                speech_pad_ms=200,            # 段首尾补 200ms，防止吞掉词首/词尾
                max_speech_duration_s=30,     # 超长段强制切分，避免单段过长丢字
            )
        # 4) 跨句上下文：condition_on_previous_text 让相邻句共享语境，专有名词更连贯。
        # 5) 温度回退：首遍差时自动升温(0→0.5→1.0)重解，降低硬句的错字率。
        print(f"[Whisper] lang={lang} vad={use_vad} prompt={'自定义' if os.environ.get('WHISPER_PROMPT') else '默认'}",
              flush=True)
        segments, _ = model.transcribe(
            wav_path,
            language=lang,
            beam_size=5,
            vad_filter=use_vad,
            vad_parameters=vad_parameters,
            initial_prompt=prompt,
            condition_on_previous_text=True,
            temperature=[0.0, 0.5, 1.0],
        )
        return "".join(seg.text for seg in segments).strip()


class LocalSenseVoiceASR:
    """基于阿里 FunAudioLLM SenseVoice 的离线识别（语音不出本机，自带标点 / ITN）。

    默认模型 iic/SenseVoiceSmall（ModelScope），支持中 / 英 / 粤 / 日 / 韩多语种，
    输出自带标点与逆文本归一化（数字转阿拉伯数字）。可用环境变量：
        SENSEVOICE_MODEL  模型名（默认 iic/SenseVoiceSmall）
        SENSEVOICE_DEVICE 推理设备（默认 cpu；有 CUDA 可填 cuda:0）
    """

    def __init__(self, model=None, device=None):
        self.model_name = (model or os.environ.get("SENSEVOICE_MODEL", "iic/SenseVoiceSmall")).strip() or "iic/SenseVoiceSmall"
        self.device = (device or os.environ.get("SENSEVOICE_DEVICE", "cpu")).strip() or "cpu"
        # 语种：默认 zh。SenseVoice 的 language="auto" 在 CPU + 短中文句上极易误判成
        # 日/韩/粤语，导致满屏错字、错误率 100%。中文场景强制 zh 准确率远高于 auto。
        # 需要识别其它语种时再经 SENSEVOICE_LANG 覆盖（如 auto / en / ja / ko / yue）。
        self.language = (os.environ.get("SENSEVOICE_LANG", "zh")).strip() or "zh"
        # 批大小：默认 1（整段一次推理，不切分）。长录音设大（如 64）才会触发 VAD
        # 自动切分，避免长句被截断丢字、输出更完整。CPU 上越大越慢，按需调整。
        self.batch_size = int((os.environ.get("SENSEVOICE_BATCH", "1")).strip() or "1")
        # 模型保存目录：TypMic/models/<模型名>，每个模型独立文件夹，互不干扰
        short = self.model_name.split("/")[-1]
        self.cache_dir = _MODELS_DIR / short

    def ready(self):
        try:
            import funasr  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_model(self):
        global _SV_MODEL
        if _SV_MODEL is None:
            # 权重下载到 TypMic/models/<模型名>（每个模型独立文件夹，互不干扰）
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("MODELSCOPE_CACHE", str(self.cache_dir))
            print(f"[SenseVoice] 模型目录: {self.cache_dir}", flush=True)
            from funasr import AutoModel
            with _SV_LOCK:
                if _SV_MODEL is None:
                    # 对齐官方最简用法（纯 CPU 办公机三行跑通，无需额外配置）：
                    #   from funasr import AutoModel
                    #   m = AutoModel(model="iic/SenseVoiceSmall", trust_remote_code=True)
                    #   m.generate(input="x.wav", language="auto", use_itn=True)[0]["text"]
                    # device 默认 cpu；有 CUDA 可经 SENSEVOICE_DEVICE 指定。
                    # trust_remote_code=True：SenseVoiceSmall 自带自定义 model.py，
                    # 多数 funasr 版本需要它才能加载（与 start.bat 预下载调用保持一致）。
                    _SV_MODEL = AutoModel(model=self.model_name, device=self.device, trust_remote_code=True)
        return _SV_MODEL

    async def transcribe(self, wav_path):
        if not self.ready():
            raise RuntimeError(
                "SenseVoice 离线模式需要 funasr + modelscope。请先安装：\n"
                "  pip install funasr modelscope\n"
                "并确认已设置 TYPOMIC_ASR=sensevoice。"
            )
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_transcribe, wav_path)

    def _sync_transcribe(self, wav_path):
        model = self._get_model()
        # 诊断：打印音频元信息，确认喂给模型的是 16k 单声道 wav（而不是损坏/静音）
        try:
            import soundfile as sf
            info = sf.info(wav_path)
            audio_desc = f"sr={info.samplerate}Hz ch={info.channels} dur={info.duration:.2f}s"
        except Exception as _e:
            audio_desc = f"(无法读取音频元信息: {_e})"
        print(f"[SenseVoice] 输入: {wav_path} | {audio_desc} | lang={self.language} "
              f"| model={self.model_name} device={self.device}", flush=True)
        # 官方最简调用：language 默认 zh（避免 auto 误判语种），use_itn=True 逆文本归一化
        # batch_size 影响长音频完整性（>1 触发 VAD 切分，默认 1 不切分）
        res = model.generate(input=wav_path, language=self.language, use_itn=True,
                             batch_size=self.batch_size)
        raw = res[0]["text"] if res and isinstance(res, list) else ""
        text = self._postprocess(raw)
        print(f"[SenseVoice] 原始输出: {raw!r}", flush=True)
        print(f"[SenseVoice] 处理后  : {text!r}", flush=True)
        return text

    # 事件标签：纯事件段（笑声/咳嗽等，无有效文字）应输出空，主链路走「未识别到语音」
    _EVENT_RE = re.compile(r"<\|(?:BGM|Applause|Laughter|Cry|Sneeze|Breath|Cough)\|>")

    def _postprocess(self, raw):
        # 优先用官方富文本后处理（ITN / 标点规整更完整）；失败回退手写正则
        text = raw
        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
            text = rich_transcription_postprocess(raw)
        except Exception:
            text = re.sub(r"<\|[^|]+\|>", "", raw)
        # 兜底去残留标签（官方后处理也可能保留部分标记）
        text = re.sub(r"<\|[^|]+\|>", "", text).strip()
        # 事件过滤：只有事件标签、无有效文字 → 返回空，不污染光标
        if not text and self._EVENT_RE.search(raw):
            return ""
        return text
