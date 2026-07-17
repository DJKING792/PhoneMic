# Contributing to TypMic

Thanks for your interest in improving TypMic! Contributions of all kinds are welcome — bug reports, docs, translations, and code.

## Before you start

- Search [existing issues](https://github.com/DJKING792/TypMic/issues) to avoid duplicates.
- For anything non-trivial (new feature, behavior change), please **open an issue first** to discuss the approach.

## Reporting bugs

Open an issue and include:

- Your OS (Windows / macOS / Linux) and version
- Python version (`python --version`)
- What you did, what you expected, and what happened
- The server's startup diagnostic output (IP / ffmpeg / cert / port / key status)

## Development setup

```bash
git clone https://github.com/DJKING792/TypMic.git
cd TypMic
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in MIMO_API_KEY
python voice_input_server.py
```

## Coding conventions

- **Python**: formatted with Black, typed where reasonable, keep functions small.
- **`.bat` scripts (Windows) are a hard rule**: must be saved as **GBK / ANSI encoding, CRLF line endings, no BOM**. UTF-8 or LF will break Chinese text on a default Windows console.
- **HTML/JS**: vanilla, no build step. Keep `index.html` (phone page) and `desktop.html` (status page) in sync if you change shared behavior.
- Commit messages: short imperative summary in English (e.g. `fix: handle empty audio chunk`).

## Pull requests

1. Fork and create a branch off `main` (`fix/...`, `feat/...`).
2. Keep PRs focused and small.
3. Make sure the server still starts and the startup diagnostics print cleanly.
4. Update `README.md` / `README.zh-CN.md` if behavior changes.

By contributing you agree your contributions are licensed under the [MIT License](LICENSE).
