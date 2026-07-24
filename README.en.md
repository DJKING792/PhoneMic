<p align="center">
  <a href="README.md">📖 中文文档</a>
</p>

<p align="center">
  <img src="assets/banner.png" alt="TypMic" width="700">
</p>

<h1 align="center">TypMic</h1>

<p align="center">Scan a QR code in your phone's browser to connect instantly — audio stays on your own LAN and never leaves your network. Multiple ASR engines (Xiaomi MiMo cloud + local Whisper / SenseVoice), a glossary that fixes mis-heard terms, and optional AI polish turn your dictation straight into usable text. Windows / macOS / Linux.</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/ASR-MiMo%20%7C%20Whisper%20%7C%20SenseVoice-orange?style=flat-square" alt="ASR Engine">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  <img src="https://github.com/DJKING792/TypMic/actions/workflows/ci.yml/badge.svg" alt="CI">
</p>

## Contents

- [How it works](#how-it-works)
- [Quick Start](#quick-start)
  - [Download the project](#download-the-project)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Connect your phone](CONNECT_PHONE.en.md)

## Real usage statistics

![Usage count](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/DJKING792/GIST_ID/raw/stats_count.json)
![Characters typed](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/DJKING792/GIST_ID/raw/stats_chars.json)

## Compared with similar tools

| Aspect | TypMic (this project) | Most similar tools |
| --- | --- | --- |
| Phone side | Record in the phone browser, scan to start, no app install | Require an app, or depend on a specific phone IME |
| Recognition | Xiaomi MiMo cloud (Chinese / dialects / Chinese-English mix) + local faster-whisper / SenseVoice offline modes | Usually a single engine / single option |
| Control keys | Built-in Enter / New-line / Backspace / Clear buttons, standard key events, cross-platform | Often rely on Windows-only AutoHotkey scripts |
| Cross-platform | Works on Windows / macOS / Linux, no platform lock-in | Often Windows-only |
| Network & privacy | Pure LAN, data never leaves your network; offline mode keeps audio fully on-device | Often via public internet / third-party relay |

## How it works

```
Phone browser                PC (runs this service)
    |                              |
    |---- record (HTTPS POST) --->|  /api/transcribe
    |                              |      ↓ ffmpeg → 16 kHz mono wav
    |                              |      ↓ MiMo-V2.5-ASR cloud API   (Cloud Mode)
    |                              |      ↓ local Whisper / SenseVoice model   (Offline Mode)
    |<--- return transcript -------|      ↓ copy to clipboard + Ctrl+V into cursor
```

<p align="center">
  <img src="assets/demo.gif" alt="TypMic demo: speak to your phone, text appears on your PC" width="640">
</p>

The text is only ever typed into the cursor of **the PC that runs this service**; the phone (or any other LAN device) acts purely as a "wireless microphone".

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org) (must be on your `PATH`)
- A PC + a phone on the same Wi-Fi
- A Xiaomi MiMo API key **(Cloud Mode only)** — see [Getting a free MiMo API key](#getting-a-free-mimo-api-key). *Skip this if you use Offline Mode.*

## Quick Start

### Download the project

1. Open the **Releases** page of the GitHub repo.
2. Download the latest archive.
3. Unzip it to any folder.
4. Enter the unzipped **`TypMic`** folder — all the Windows / macOS steps below run from inside it.

### Windows

1. Get a Xiaomi MiMo API key at <https://platform.xiaomimimo.com> (register, then create an API key). *Only needed for Cloud Mode; skip it if you use Offline Mode.*
2. **Allow the firewall first**: right-click `allow_firewall.bat` → "Run as administrator" (opens port 8443; one time only). If the phone later shows "connection refused / ERR_CONNECTION_REFUSED", this step was likely skipped.
3. Double-click `start.bat`
   - On first run it creates a virtualenv and installs dependencies automatically.
   - It then **asks you to choose the recognition mode**: `1) Cloud (MiMo)` / `2) Offline (faster-whisper)` / `3) Offline (SenseVoice)`. Offline mode skips the API-key prompt and installs the local ASR dependency automatically; your choice is remembered in `.env` for next time.
   - It also asks about **AI polish** (default: off) and **glossary** (default: on); just press Enter to accept the defaults — no config needed.
   - If you pick Cloud Mode and no key is found, it **prompts you to enter one**, then writes it to `.env` automatically.
4. The screen shows the "phone URL" (e.g. `https://192.168.x.x:8443`) and a QR code.
5. Connect your phone by OS (see [Connect your phone](CONNECT_PHONE.en.md)).
6. Put the PC cursor wherever you want text (Notepad / WeChat / browser…) and just speak into the phone.

### macOS

1. **Install ffmpeg** (for transcoding; pip can't install it): `brew install ffmpeg` (no Homebrew? get it at [brew.sh](https://brew.sh)).
2. **Grant permissions** (System Settings → Privacy & Security): allow **Python** through the Firewall, and enable **Terminal** under Accessibility (else the phone can't connect or text won't type).
3. **`cd` into the project and run it:**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MIMO_API_KEY=your_key    # or put MIMO_API_KEY=your_key in a .env at the project root
python voice_input_server.py
```

**Offline Mode** (no API key; audio never leaves your Mac): drop the `export MIMO_API_KEY` line above and end with these instead — the recognition model is downloaded automatically on first run. `TYPOMIC_ASR` can be `whisper` (faster-whisper) or `sensevoice` (SenseVoice, with built-in punctuation / inverse text normalization):

```bash
# install one local engine (only that engine; whisper does NOT pull torch):
pip install -r requirements-whisper.txt      # whisper engine
# pip install -r requirements-sensevoice.txt # sensevoice engine (ships CPU-only torch)
export TYPOMIC_ASR=whisper                   # or sensevoice
python voice_input_server.py

> **Improve Whisper accuracy** (already tuned for Chinese by default, no extra step needed): `WHISPER_LANG` forces the language (default `zh`; set `auto` to auto-detect); `WHISPER_VAD` silence filtering (default `on`); `WHISPER_PROMPT` custom prompt. For higher accuracy set `WHISPER_MODEL=medium` (larger and slower).
```

After startup the screen shows the "phone URL" and QR code — then connect your phone (see [Connect your phone](CONNECT_PHONE.en.md)).

## Getting a free MiMo API key

Cloud Mode needs a free Xiaomi MiMo API key. Get one in 3 steps:

<details>
<summary>📌 Click to expand: 3-step illustrated guide to a free MiMo API key</summary>

**1. Register / log in** at <https://platform.xiaomimimo.com> (Xiaomi account)

![Step 1 — register / log in](assets/mimo-key/mimo-step1-register.png)

**2. Console → "API Keys" in the left sidebar**

![Step 2 — API keys page](assets/mimo-key/mimo-step2-keys.png)

**3. Create a key → copy it immediately** (shown only once) into `.env`: `MIMO_API_KEY=your_key`

![Step 3 — create & copy the key](assets/mimo-key/mimo-step3-create.png)

</details>

> ⚠️ **Cost note (read before enabling AI polish)**
> Signing up at Xiaomi MiMo's platform (platform.xiaomimimo.com) gives you a **¥10 API trial credit (valid 40 days)**. At ~30 min of daily dictation it lasts **a month or more** during the trial phase. After it runs out you can top up by usage (real-name verification required). For **zero cost**, turn off AI polish and use Offline Mode — offline recognition runs on your PC and calls no MiMo API at all.

## AI polish & glossary (optional)

TypMic enables two post-processing steps by default: **auto-punctuation** + **correcting mis-heard terms** (e.g. product names) so the dictated text is ready to use. Both can be toggled in the `start.bat` launch menu; **on by default, no config needed**.

> When AI polish is on, the recognized text is sent to your MiMo endpoint for cleanup. To keep everything fully local, just turn it off in the menu (audio always stays on your LAN).

## FAQ

<details>
<summary>❓ How much latency is there?</summary>

In **Cloud Mode** a typical utterance (a sentence or two) takes about **1–2 seconds** end-to-end — phone capture + LAN upload + MiMo ASR + paste. In **Offline Mode** it depends on model size and hardware: a `small` model on CPU is usually a few hundred ms to ~1–2 s per utterance; a GPU or `tiny`/`base` model is faster.

</details>

<details>
<summary>❓ How long can a single clip be?</summary>

There is no hard cap, but each "press-and-hold" is one clip. For best accuracy and lowest latency keep a clip to roughly **tens of seconds to a couple of minutes**; long dictation is best done as a series of short clips — the text streams into your cursor continuously.

</details>

<details>
<summary>❓ Does it work without internet?</summary>

**Cloud Mode** needs internet (to reach MiMo's ASR API), but your **audio is only ever sent across your own LAN to the PC** — it never passes through any third-party relay. If you need **zero internet**, enable **Offline Mode** (`TYPOMIC_ASR=whisper` or `=sensevoice`): recognition runs entirely on your PC and works fully offline.

</details>

<details>
<summary>❓ Is my audio private?</summary>

In Cloud Mode, audio leaves your LAN only to reach Xiaomi's ASR endpoint for transcription, and TypMic stores nothing. In Offline Mode the audio never leaves the PC at all.

</details>

<details>
<summary>❓ The phone can't connect / "connection refused"?</summary>

On startup the server prints detailed diagnostics (IP / ffmpeg / cert / port / key status) — check there. The PC page `https://localhost:8443/desktop` also has a live connection-status view. Most "refused" cases are the firewall blocking port 8443 (see Quick Start).

</details>

## License

[MIT](LICENSE) © TypMic contributors.

## Contributing & Support

- Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).
- Found a vulnerability? Please follow [SECURITY.md](SECURITY.md).
- Need help? Check [SUPPORT.md](SUPPORT.md).
