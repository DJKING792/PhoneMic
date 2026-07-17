"""本地离线语音识别后端（faster-whisper）。

可选功能：设置环境变量 TYPOMIC_ASR=local 后启用。
- 不需要任何云端 API key，识别完全在本机完成（音频不出本机 / 局域网之外的公网）。
- 首次使用会自动下载 Whisper 模型权重（约几百 MB，仅一次）。
- 依赖 faster-whisper 为【可选】安装，不污染核心依赖：
      pip install faster-whisper
"""

import os
import threading

_LOCK = threading.Lock()
_MODEL = None


class LocalWhisperASR:
    """基于 faster-whisper 的离线识别（语音不出本机）。"""

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
            with _LOCK:
                if _MODEL is None:
                    _MODEL = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        return _MODEL

    async def transcribe(self, wav_path):
        if not self.ready():
            raise RuntimeError(
                "离线模式需要 faster-whisper。请先安装：\n"
                "  pip install faster-whisper\n"
                "并确认已设置 TYPOMIC_ASR=local。"
            )
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_transcribe, wav_path)

    def _sync_transcribe(self, wav_path):
        model = self._get_model()
        segments, _ = model.transcribe(wav_path, language=None, beam_size=5)
        return "".join(seg.text for seg in segments).strip()
