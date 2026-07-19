#!/usr/bin/env python3
"""文本后处理：术语表修正 + 可选 AI 润色。

两个能力，都可独立开关，且失败一律降级为「返回原文」，绝不阻断粘贴：

1. 术语表（glossary）：把常被识别错的产品名 / 人名 / 英文工具名纠正回来。
   读取同目录 glossary.txt，每行一条规则，两种写法：
       klawd => Claude          # 错词 => 正词（大小写不敏感匹配）
       Cursor                   # 单独一个词 = 告诉润色模型「优先用这个写法」
   `=>` 规则做**文本替换**（识别后立刻纠正，最稳）；
   单词条目作为**术语偏好**注入润色提示，让 LLM 倾向用它。

2. AI 润色（polish）：把口语化的识别原文整理成能直接用的文本——
   去口头禅、顺句、自动分段、数字/金额规范、明显口误自纠。
   走 OpenAI 兼容的 chat/completions 接口，模型可自由配置。

设计原则：润色是「增益」不是「依赖」。任一环节报错都返回上一步文本，
保证「识别 → 粘贴」主链路永远不被润色拖垮。
"""

import re
from pathlib import Path

import aiohttp


# --------------------------------------------------------------------------- #
# 术语表
# --------------------------------------------------------------------------- #
def load_glossary(path):
    """读取 glossary.txt，返回 (replacements, terms)。

    replacements: [(wrong, right), ...]  用于文本替换（=> 规则）
    terms:        ["Cursor", "TypMic", ...]  用于注入润色提示的术语偏好
    文件不存在或为空时返回 ([], [])，调用方据此自动跳过。
    """
    p = Path(path)
    if not p.exists():
        return [], []
    replacements = []
    terms = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=>" in line:
                    wrong, _, right = line.partition("=>")
                    wrong, right = wrong.strip(), right.strip()
                    if wrong and right:
                        replacements.append((wrong, right))
                        terms.append(right)
                else:
                    terms.append(line)
    except Exception:
        return [], []
    # 术语去重，保序
    seen = set()
    uniq_terms = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            uniq_terms.append(t)
    return replacements, uniq_terms


def apply_glossary(text, replacements):
    """按 replacements 做大小写不敏感的整词/子串替换。失败返回原文。"""
    if not text or not replacements:
        return text
    out = text
    try:
        for wrong, right in replacements:
            # 大小写不敏感替换；wrong 里的正则元字符做转义
            out = re.sub(re.escape(wrong), right, out, flags=re.IGNORECASE)
    except Exception:
        return text
    return out


# --------------------------------------------------------------------------- #
# AI 润色
# --------------------------------------------------------------------------- #
DEFAULT_SYSTEM_PROMPT = (
    "你是一个中文语音输入的文本整理助手。用户会给你一段语音识别的原始文本"
    "（通常没有标点、口语化、可能有口头禅和同音口误）。请把它整理成可以直接粘贴使用的书面文本。\n\n"
    "【最重要】第一条规则：必须补全符合中文书写习惯的标点符号。根据语义和自然停顿，"
    "补上逗号、句号、顿号、分号、冒号、引号、书名号、问号、感叹号等。"
    "绝对不要输出一整段没有标点的纯文本。\n\n"
    "【命令词】若用户以指令口吻说出下列词，请转化为对应的格式或标点，而不是保留这几个字：\n"
    "- 「新段落」「换行」「另起一段」「分段」→ 在对应位置插入一个空行（分段）\n"
    "- 「句号」「点」→ 。\n"
    "- 「逗号」→ ，\n"
    "- 「问号」→ ？\n"
    "- 「感叹号」→ ！\n"
    "- 「冒号」→ ：\n"
    "- 「分号」→ ；\n\n"
    "【整理规则】\n"
    "1. 轻度去掉「呃、啊、那个、就是、然后、嗯」等口头禅和无意义重复，但不要过度删改，保留用户原意与措辞；\n"
    "2. 顺句、修正明显的同音口误（如「不是周五，是周四」直接写成「周四」）；\n"
    "3. 内容较长或有并列要点时，自动分段或列成条目；\n"
    "4. 规范数字、金额（如「三千六」写成「¥3,600」）、时间与单位；\n"
    "5. 技术术语、代码、英文标识符、专有名词保持原样，不要「翻译」或改写；\n"
    "6. 严格保持原意：不要扩写、不要添加原文没有的信息、不要回答其中的问题；\n"
    "7. 只输出整理后的正文，不要任何解释、前言，也不要用引号包裹整段。"
)


class Polisher:
    """OpenAI 兼容 chat/completions 润色客户端。

    参数均可通过环境变量配置（见 voice_input_server 里的读取逻辑）。
    ready() 为 False 时调用方应跳过润色。
    """

    def __init__(self, api_url, api_key, model, system_prompt=None, timeout=30):
        self.api_url = (api_url or "").strip()
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.timeout = timeout

    def ready(self):
        return bool(self.api_url and self.api_key and self.model)

    async def polish(self, text, terms=None):
        """润色文本。任何异常都返回原文（降级），绝不抛出打断主链路。"""
        if not text or not text.strip() or not self.ready():
            return text

        sys_prompt = self.system_prompt
        if terms:
            sys_prompt += (
                "\n\n以下是用户的专有名词/术语表，若原文出现相近发音或写法，"
                "请优先使用这些标准写法：" + "、".join(terms) + "。"
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "api-key": self.api_key,  # 兼容小米等用 api-key 头的服务
            "Content-Type": "application/json",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, json=payload, headers=headers, timeout=timeout
                ) as resp:
                    if resp.status != 200:
                        return text
                    data = await resp.json()
            polished = data["choices"][0]["message"]["content"]
            polished = (polished or "").strip().strip('"').strip("'").strip()
            return polished or text
        except Exception:
            return text
