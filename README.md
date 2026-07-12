<p align="center">
  <a href="README.en.md">📖 English</a>
</p>

<p align="center">
  <img src="assets/banner.png" alt="PhoneMic" width="700">
</p>

<h1 align="center">PhoneMic</h1>

<p align="center"><b>手机当麦克风：说话即转文字，自动输入电脑光标。</b></p>
<p align="center">手机浏览器录音 → 音频经局域网 HTTPS 上传 → 小米 MiMo-V2.5-ASR 云端识别 → 文字自动粘贴到电脑当前光标。无需装 App、无需数据线，扫码即用。</p>
<p align="center">把手机变成电脑的「无线麦克风」——写长文、聊微信、写代码注释、做字幕，对着手机说话就能打字。</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/ASR-MiMo%20V2.5-orange?style=flat-square" alt="ASR Engine">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

## 目录

- [功能](#功能)
- [使用场景](#使用场景)
- [工作原理](#工作原理)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
  - [Windows](#windows)
  - [macOS / Linux](#macos--linux)
  - [手机连接](#手机连接)
  - [重新生成证书](#重新生成证书)
- [安全说明](#安全说明)
- [常见问题](#常见问题)
- [许可证](#许可证)
- [贡献与支持](#贡献与支持)

## 功能

- 🎙️ 手机浏览器录音，扫码即开
- ☁️ 小米 MiMo 云端识别（中文 / 方言 / 中英混说，自带标点）
- ⌨️ 识别结果自动粘贴到电脑当前光标
- 🔌 纯局域网，自签 HTTPS

## 使用场景

- 📝 **写长文 / 论文 / 博客**：不想一直敲键盘，对着手机说，文字直接进文档光标。
- 💬 **微信 / QQ / 钉钉 聊天**：光标放到输入框，说话即输入，免打字。
- 💻 **写代码注释 / 提交信息**：顺手口述，自动落到编辑器光标。
- 🎬 **字幕 / 会议纪要录入**：实时语音转文字，省去后期整理。
- 🗣️ **语音输入法替代**：不装第三方输入法，也能在任意有光标的地方语音输入。

> 相关搜索词：手机当麦克风、无线麦克风、语音输入、语音转文字、局域网语音识别、对着手机说话打字、免安装语音输入、MiMo 语音识别、电脑语音输入。

## 工作原理

```
手机浏览器                  电脑（运行本服务）
    |                           |
    |---- 录音(HTTPS POST) ---->|  /api/transcribe
    |                           |      ↓ ffmpeg 转 16k 单声道 wav
    |                           |      ↓ 调用 MiMo-V2.5-ASR 云端 API
    |<--- 返回识别文本 ---------|      ↓ 复制到剪贴板 + Ctrl+V 粘贴到光标
```

文字只会输入到**运行本服务的那台电脑**的光标里；手机（或其他局域网设备）扮演的是「无线麦克风」的角色。

## 环境要求

- Python 3.10+
- [ffmpeg](https://ffmpeg.org)（需加入系统 PATH）
- 一台电脑 + 同一 WiFi 下的手机

## 快速开始

### Windows

1. 申请小米 MiMo API key：<https://mimo.mi.com>（注册后创建 API key）
2. **首次使用先放行防火墙**：右键 `allow_firewall.bat` →「以管理员身份运行」（放行 8443 端口，只需一次）。若之后手机仍提示「已拒绝连接 / ERR_CONNECTION_REFUSED」，多半是这一步没做。
3. 双击 `start.bat`
   - 首次会自动创建虚拟环境并安装依赖
   - 若未检测到 key，会**提示你输入**，输入后自动写入 `.env`
4. 屏幕会显示「手机访问地址」（如 `https://192.168.x.x:8443`）以及二维码
5. 按手机系统完成连接（见下方「手机连接」）
6. 电脑上把光标放到要输入的位置（记事本 / 微信 / 浏览器等），手机说话即可自动输入

### macOS / Linux

1. 打开「终端」（Terminal），进入项目目录。
2. 依次执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MIMO_API_KEY=你的key    # 也可直接创建同目录 .env 并写入 MIMO_API_KEY=你的key（服务端会自动读取）
python voice_input_server.py
```

3. **放行端口 8443**（手机才能连上）：
   - **macOS**：需在「系统设置 → 隐私与安全性 → 防火墙」允许 **Python** 接收传入连接；首次运行时弹出的网络访问请求点「允许」。若曾拒绝，需在防火墙选项里把 Python 设为允许。
   - **Linux（ufw）**：`sudo ufw allow 8443`。

启动后屏幕会显示「手机访问地址」和二维码，然后按下方「手机连接」操作。

### 手机连接

**安卓手机**

1. 扫码页面的二维码，或直接输入网址访问。
2. 浏览器提示「证书风险 / 不安全」时，点「高级 → 继续访问」即可正常使用。

**iPhone（以下步骤仅 iPhone 需要，安卓无需）**

自签证书在生成时已把局域网 IP 写进 SAN，且有效期 ≤398 天，符合苹果要求——但 iOS 仍需手动信任。

#### 第 1 步：把根证书传到 iPhone

1. 证书文件在服务端的**项目根目录** `rootCA.pem`。
2. 用 **AirDrop / 邮件 / 微信文件 / 云盘** 等任意方式，把 `rootCA.pem` 传到 iPhone。
3. 在 iPhone 上打开该文件（或从「文件」App 打开），按提示**安装描述文件**；若未自动跳转，到「**设置 → 通用 → VPN 与设备管理**」（旧版 iOS 叫「描述文件」）中手动点开并安装。

#### 第 2 步：激活证书的「完全信任」

**光安装描述文件不够。** 进入「**设置 → 通用 → 关于本机 → 证书信任设置**」，在下方找到本项目自签证书，**手动打开「完全信任」开关**。不开启这一步，Safari 仍会判定为不安全并拒绝连接。

#### 第 3 步：打开页面

证书信任后，再在 iPhone 打开 `https://<电脑IP>:8443`（或扫电脑端 `https://<电脑IP>:8443/desktop` 的二维码），地址栏不再有证书警告，即可正常「按住说话」。

### 需要重新生成证书的情形

证书在生成时只写入当时的局域网 IP；若电脑 IP 变了（DHCP 重新分配），需重新生成：删除**项目根目录**下的 4 个证书文件（`cert.pem`、`key.pem`、`rootCA.pem`、`rootCA-key.pem`）后重启服务即可（新证书会写入当前 IP）。

## 安全说明

- 监听 `0.0.0.0:8443` 且默认不加鉴权——刻意设计，仅限**可信局域网**使用。
- API key 只在本地 `.env`（已被 `.gitignore` 屏蔽），证书为本地自签，均不上传仓库。

## 常见问题

启动时会打印详细诊断信息（IP / ffmpeg / 证书 / 端口 / key 状态），连接问题看这里即可；电脑端 `https://localhost:8443/desktop` 还有实时连接状态页。

## 许可证

[MIT](LICENSE) © PhoneMic 贡献者。

## 贡献与支持

- 想参与开发？请看 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 发现安全漏洞？请遵循 [SECURITY.md](SECURITY.md)。
- 需要帮助？查看 [SUPPORT.md](SUPPORT.md)。
