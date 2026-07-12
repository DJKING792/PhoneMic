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
  <img src="https://img.shields.io/badge/ASR-MiMo%20V2.5-orange?style=flat-square" alt="ASR Engine">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

## Contents

- [Features](#features)
- [Use cases](#use-cases)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
  - [Windows](#windows)
  - [macOS / Linux](#macos--linux)
  - [Connect your phone](#connect-your-phone)
  - [Regenerate the certificate](#regenerate-the-certificate)
- [Security](#security)
- [FAQ](#faq)
- [License](#license)
- [Contributing & Support](#contributing--support)

## Features

- 🎙️ Record from your phone's browser — scan a QR code and go.
- ☁️ Xiaomi MiMo cloud ASR (Chinese / dialects / Chinese-English mix, with automatic punctuation).
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
    |                              |      ↓ call MiMo-V2.5-ASR cloud API
    |<--- return transcript -------|      ↓ copy to clipboard + Ctrl+V into cursor
```

The text is only ever typed into the cursor of **the PC that runs this service**; the phone (or any other LAN device) acts purely as a "wireless microphone".

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org) (must be on your system `PATH`)
- A PC + a phone on the same Wi-Fi

## Quick Start

### Windows

1. Get a Xiaomi MiMo API key at <https://mimo.mi.com> (register, then create an API key).
2. **Allow the firewall first**: right-click `allow_firewall.bat` → "Run as administrator" (opens port 8443; one time only). If the phone later shows "connection refused / ERR_CONNECTION_REFUSED", this step was likely skipped.
3. Double-click `start.bat`.
   - On first run it creates a virtualenv and installs dependencies automatically.
   - If no key is found, it **prompts you to enter one**, then writes it to `.env` automatically.
4. The screen shows the "phone URL" (e.g. `https://192.168.x.x:8443`) and a QR code.
5. Connect your phone (see [Connect your phone](#connect-your-phone) below).
6. Put the PC cursor wherever you want text (Notepad / WeChat / browser…) and just speak into the phone.

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

3. **Open port 8443** (so the phone can connect):
   - **macOS**: allow **Python** to accept incoming connections in System Settings → Privacy & Security → Firewall. Approve the network prompt on first run. If you once denied it, re-enable Python in the firewall options.
   - **Linux (ufw)**: `sudo ufw allow 8443`.

After startup the screen shows the "phone URL" and QR code — then follow [Connect your phone](#connect-your-phone).

### Connect your phone

**Android**

1. Scan the QR code on the page, or just type the URL.
2. When the browser warns "certificate risk / not secure", tap "Advanced → Proceed" and it works normally.

**iPhone** *(these steps are iPhone-only; Android needs none of them)*

The self-signed certificate already includes the LAN IP in its SAN and is valid for ≤398 days, so it complies with Apple's requirements — but iOS still needs manual trust.

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

## Security

- It listens on `0.0.0.0:8443` with **no auth by design** — intended for a **trusted LAN only**.
- The API key lives only in the local `.env` (blocked by `.gitignore`); the certificate is a local self-sign and is never committed.

## FAQ

On startup the server prints detailed diagnostics (IP / ffmpeg / cert / port / key status) — check there for connection issues. The PC page `https://localhost:8443/desktop` also has a live connection-status view.

## License

[MIT](LICENSE) © PhoneMic contributors.

## Contributing & Support

- Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).
- Found a vulnerability? Please follow [SECURITY.md](SECURITY.md).
- Need help? Check [SUPPORT.md](SUPPORT.md).
