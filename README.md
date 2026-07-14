<p align="center">
  <a href="README.zh-CN.md">📖 中文文档</a>
</p>

<p align="center">
  <img src="assets/banner.png" alt="PhoneMic" width="700">
</p>

<h1 align="center">PhoneMic</h1>

<p align="center"><b>Turn your phone into a wireless microphone for your PC.</b></p>
<p align="center">Record in your phone's browser → audio is sent over LAN HTTPS → transcribed by Xiaomi MiMo-V2.5-ASR → the text is pasted into your PC's cursor. No app install, no USB cable — just scan a QR code.</p>
<p align="center">Use your phone as a wireless microphone for your PC — draft long texts, chat, write code comments, or caption videos by just speaking.</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/ASR-MiMo%20V2.5%20%7C%20Whisper-orange?style=flat-square" alt="ASR Engine">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

## Contents

- [Features](#features)
- [Use cases](#use-cases)
- [How it works](#how-it-works)
- [Pro / Offline Mode (local ASR)](#pro--offline-mode-local-asr)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
  - [Windows](#windows)
  - [macOS / Linux](#macos--linux)
  - [Connect your phone](#connect-your-phone)
  - [Regenerate the certificate](#regenerate-the-certificate)
- [Getting a free MiMo API key](#getting-a-free-mimo-api-key)
- [Security](#security)
- [FAQ](#faq)
- [License](#license)
- [Contributing & Support](#contributing--support)

## Features

- 🎙️ Record from your phone's browser — scan a QR code and go.
- ☁️ Xiaomi MiMo cloud ASR (Chinese / dialects / Chinese-English mix, with automatic punctuation).
- 🖥️ **Optional offline mode** — switch to local [faster-whisper](#pro--offline-mode-local-asr) and transcribe fully on your PC: no API key, no internet needed.
- ⌨️ Transcription is auto-pasted into the PC's active cursor.
- 🔌 Pure LAN, self-signed HTTPS.

## Use cases

- 📝 **Long-form writing** (articles, essays, blogs) — use your phone as a microphone and voice-input long texts by just speaking.
- 💬 **Chat in WeChat / Slack / Discord** — a no-install voice input: put the cursor in the box and speak to send.
- 💻 **Code comments & commit messages** — dictate and the transcript drops into your editor's cursor.
- 🎬 **Subtitles & meeting notes** — LAN voice recognition turns speech to text in real time.
- 🗣️ **A voice-input-method replacement** — no third-party IME; your phone becomes a wireless microphone for PC voice input anywhere there's a cursor.

## How it works

```
Phone browser                PC (runs this service)
    |                              |
    |---- record (HTTPS POST) --->|  /api/transcribe
    |                              |      ↓ ffmpeg → 16 kHz mono wav
    |                              |      ↓ MiMo-V2.5-ASR cloud API   (Cloud Mode)
    |                              |      ↓ faster-whisper local model   (Offline Mode)
    |<--- return transcript -------|      ↓ copy to clipboard + Ctrl+V into cursor
```

<p align="center">
  <img src="assets/demo.gif" alt="PhoneMic demo: speak to your phone, text appears on your PC" width="640">
</p>

The text is only ever typed into the cursor of **the PC that runs this service**; the phone (or any other LAN device) acts purely as a "wireless microphone".

## Pro / Offline Mode (local ASR)

By default PhoneMic uses Xiaomi's MiMo cloud ASR. If you want everything to stay on your PC — no API key, no internet, fully private — enable **Offline Mode** with a local faster-whisper model. See [requirements-offline.txt](requirements-offline.txt) for details.

⚠️ Offline Mode's Chinese recognition is limited. Whisper is trained mainly on English and is noticeably weaker than MiMo cloud for Chinese (especially dialects, jargon, homophones, and Chinese-English mixing). If your main language is Chinese, Cloud Mode (MiMo) is strongly recommended. Offline Mode fits best when English / general content is the priority and "fully private / offline" comes first — and because audio never leaves the PC, it is also ideal for self-hosted / offline setups.

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org) (must be on your `PATH`)
- A PC + a phone on the same Wi-Fi
- A Xiaomi MiMo API key **(Cloud Mode only)** — see [Getting a free MiMo API key](#getting-a-free-mimo-api-key). *Skip this if you use Offline Mode.*

## Quick Start

### Windows

1. **Download the project**: Create a folder anywhere and open it. Click the File Explorer address bar, type `cmd`, and press Enter to open a command prompt in that folder. Run:

   ```
   git clone https://github.com/DJKING792/PhoneMic.git
   ```

   Then enter the created `PhoneMic` subfolder.
2. **Allow the firewall first**: right-click `allow_firewall.bat` → "Run as administrator" (opens port 8443; one time only). If the phone later shows "connection refused / ERR_CONNECTION_REFUSED", this step was likely skipped.
3. **Double-click `start.bat` to launch**: On first run it creates a virtualenv and installs dependencies automatically, then asks you to choose the mode — `1` Cloud (MiMo, prompts for a free API key; get one at <https://platform.xiaomimimo.com>) or `2` Offline (local faster-whisper, no key needed). Your choice is saved to `.env` and reused next time.
4. The screen shows the "phone URL" (e.g. `https://192.168.x.x:8443`) and a QR code.
5. Connect your phone (see [Connect your phone](#connect-your-phone) below), put the PC cursor wherever you want text (Notepad / WeChat / browser…), and just speak into the phone.

### macOS / Linux

1. Open Terminal and `cd` into the project directory.
2. Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MIMO_API_KEY=your_key    # or just create a sibling .env with MIMO_API_KEY=your_key (the server reads it automatically)
python voice_input_server.py
```

   To use **Offline Mode** instead, replace the last two lines with:

```bash
pip install faster-whisper
export PHONEMIC_ASR=local
python voice_input_server.py
```

3. **Open port 8443** (so the phone can connect):
   - **macOS**: allow **Python** to accept incoming connections in System Settings → Privacy & Security → Firewall. Approve the network prompt on first run. If you once denied it, re-enable Python in the firewall options.
   - **Linux (ufw)**: `sudo ufw allow 8443`.

After startup the screen shows the "phone URL" and QR code — then follow [Connect your phone](#connect-your-phone).

### Connect your phone

**Android**

1. Scan the QR code on the page, or just type the URL.
2. When the browser warns "certificate risk / not secure", tap "Advanced → Proceed" and it works normally.

**iPhone** *(these steps are iPhone-only; Android needs none of them)*

iOS is strict about self-signed certificates and requires manual trust. The steps:

**Step 1 — Send the root cert to the iPhone**

1. The cert file is `rootCA.pem` in the **project root** on the server.
2. Send `rootCA.pem` to the iPhone via AirDrop / Mail / WeChat Files / cloud drive — anything works.
3. Open the file on the iPhone (or from the Files app) and **install the profile** when prompted. If it doesn't auto-jump, go to **Settings → General → VPN & Device Management** (older iOS: "Profiles") and tap to install manually.

**Step 2 — Enable "full trust" for the cert**

Installing the profile alone is **not enough**. Go to **Settings → General → About → Certificate Trust Settings**, find this project's self-signed cert, and manually turn on **Full Trust**. Without this, Safari still treats it as insecure and refuses to connect.

**Step 3 — Open the page**

Once trust is enabled, open `https://<PC-IP>:8443` on the iPhone (or scan the QR code at `https://<PC-IP>:8443/desktop`). The address bar no longer warns, and you can "press and hold to talk".

### Regenerate the certificate

The certificate is generated with the LAN IP at that moment baked in. If the PC's IP changes (DHCP reassign), regenerate it: delete the 4 cert files in the **project root** (`cert.pem`, `key.pem`, `rootCA.pem`, `rootCA-key.pem`) and restart the service (a new cert is written with the current IP).

## Getting a free MiMo API key

Cloud Mode needs a free Xiaomi MiMo API key. Get one in 3 steps:

<details>
<summary>📌 Click to expand: 3-step illustrated guide to a free MiMo API key</summary>

**Step 1 — Register / log in**

1. Open <https://platform.xiaomimimo.com> in your browser.
2. Click **登录 / Sign in** (top-right) and log in with your Xiaomi account. If you have none, tap **注册 / Register** to create one — it's free.

![Step 1 — register / log in to platform.xiaomimimo.com](assets/mimo-key/mimo-step1-register.png)

**Step 2 — Open the API keys page**

1. After logging in, go to **控制台 / Console** (usually top-right avatar menu).
2. In the left sidebar find **API 密钥 / API Keys** (or **开放平台 → 密钥管理**).
3. You should see a list of your keys (empty at first).

![Step 2 — open the API keys page](assets/mimo-key/mimo-step2-keys.png)

**Step 3 — Create & copy the key**

1. Click **创建密钥 / Create key** (or **+ 新建**).
2. Give it any name (e.g. `PhoneMic`) and confirm.
3. **Copy the key immediately** — it is shown only once. Paste it into your `.env` as `MIMO_API_KEY=你的key`, or just run `start.bat` on Windows and paste it when prompted.

![Step 3 — create & copy the key](assets/mimo-key/mimo-step3-create.png)

> 💡 The MiMo API has a free quota for personal use. Keep your key private — never commit it to a repo (PhoneMic's `.gitignore` already blocks `.env`).

</details>

## Security

- It listens on `0.0.0.0:8443` with **no auth by design** — intended for a **trusted LAN only**.
- The API key lives only in the local `.env` (blocked by `.gitignore`); the certificate is a local self-sign and is never committed.
- In **Offline Mode** no audio ever leaves the PC — recognition is fully local.

## FAQ

**Q: How much latency is there?**
A: In **Cloud Mode** a typical utterance (a sentence or two) takes about **1–2 seconds** end-to-end — phone capture + LAN upload + MiMo ASR + paste. In **Offline Mode** it depends on model size and hardware: a `small` model on CPU is usually a few hundred ms to ~1–2 s per utterance; a GPU or `tiny`/`base` model is faster.

**Q: How long can a single clip be?**
A: There is no hard cap, but each "press-and-hold" is one clip. For best accuracy and lowest latency keep a clip to roughly **tens of seconds to a couple of minutes**; long dictation is best done as a series of short clips — the text streams into your cursor continuously.

**Q: Does it work without internet?**
A: **Cloud Mode** needs internet (to reach MiMo's ASR API), but your **audio is only ever sent across your own LAN to the PC** — it never passes through any third-party relay. If you need **zero internet**, enable **Offline Mode** (`PHONEMIC_ASR=local`): recognition runs entirely on your PC and works fully offline.

**Q: Is my audio private?**
A: In Cloud Mode, audio leaves your LAN only to reach Xiaomi's ASR endpoint for transcription, and PhoneMic stores nothing. In Offline Mode the audio never leaves the PC at all.

**Q: The phone can't connect / "connection refused"?**
A: On startup the server prints detailed diagnostics (IP / ffmpeg / cert / port / key status) — check there. The PC page `https://localhost:8443/desktop` also has a live connection-status view. Most "refused" cases are the firewall blocking port 8443 (see Quick Start).

## License

[MIT](LICENSE) © PhoneMic contributors.

## Contributing & Support

- Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).
- Found a vulnerability? Please follow [SECURITY.md](SECURITY.md).
- Need help? Check [SUPPORT.md](SUPPORT.md).
