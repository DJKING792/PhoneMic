<p align="center">
  <a href="README.md">📖 English</a>
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
  <img src="https://img.shields.io/badge/ASR-MiMo%20V2.5%20%7C%20Whisper-orange?style=flat-square" alt="ASR Engine">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

## 目录

- [功能](#功能)
- [使用场景](#使用场景)
- [工作原理](#工作原理)
- [Pro / 离线模式（本地识别）](#pro--离线模式本地识别)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
  - [Windows](#windows)
  - [macOS / Linux](#macos--linux)
  - [手机连接](#手机连接)
  - [重新生成证书](#重新生成证书)
- [获取免费的小米 MiMo API Key](#获取免费的小米-mimo-api-key)
- [安全说明](#安全说明)
- [常见问题](#常见问题)
- [许可证](#许可证)
- [贡献与支持](#贡献与支持)

## 功能

- 🎙️ 手机浏览器录音，扫码即开
- ☁️ 小米 MiMo 云端识别（中文 / 方言 / 中英混说，自带标点）
- 🖥️ **可选离线模式**：切换为本地 [faster-whisper](#pro--离线模式本地识别) 识别，全程在本机完成（**以英文为主，中文识别有限**）——无需 API Key、无需联网
- ⌨️ 识别结果自动粘贴到电脑当前光标
- 🔌 纯局域网，自签 HTTPS

## 使用场景

- 📝 **写长文 / 论文 / 博客**：用手机当麦克风，语音输入长文，对着手机说话文字就进文档光标。
- 💬 **微信 / QQ / 钉钉 聊天**：免安装语音输入，光标放到输入框，说话即发，彻底告别打字。
- 💻 **写代码注释 / 提交信息**：顺手口述，识别结果自动落到编辑器光标。
- 🎬 **字幕 / 会议纪要**：基于局域网语音识别，实时把语音转成文字，省去后期整理。
- 🗣️ **替代语音输入法**：不装第三方输入法，把手机变成电脑的无线麦克风，在任意有光标的地方语音转文字。

## 工作原理

```
手机浏览器                  电脑（运行本服务）
    |                           |
    |---- 录音(HTTPS POST) ---->|  /api/transcribe
    |                           |      ↓ ffmpeg 转 16k 单声道 wav
    |                           |      ↓ 调用 MiMo-V2.5-ASR 云端 API   （云端模式）
    |                           |      ↓ faster-whisper 本地模型        （离线模式）
    |<--- 返回识别文本 ---------|      ↓ 复制到剪贴板 + Ctrl+V 粘贴到光标
```

<p align="center">
  <img src="assets/demo.gif" alt="PhoneMic 演示：对着手机说话，电脑上自动打出文字" width="640">
</p>

文字只会输入到**运行本服务的那台电脑**的光标里；手机（或其他局域网设备）扮演的是「无线麦克风」的角色。

## Pro / 离线模式（本地识别）

默认情况下 PhoneMic 使用小米 MiMo 云端识别。如果你想让一切都在本机完成——不要 API Key、不联网、完全隐私——可以开启 离线模式，更多详情见 [requirements-offline.txt](requirements-offline.txt)。

⚠️ 离线模式的中文识别效果有限。 Whisper 主要以英文训练，对中文（尤其方言、专业术语、同音词、中英混说）明显弱于 MiMo 云端。如果你的主要语言是中文，强烈建议用云端模式（MiMo）。 离线模式更适合以英文 / 通用内容为主、且把「完全隐私 / 离线」放在第一位的场景；也因其音频全程不出本机，特别适合自托管 / 离线部署。

## 环境要求

- Python 3.10+
- [ffmpeg](https://ffmpeg.org)（需加入系统 PATH）
- 一台电脑 + 同一 WiFi 下的手机
- 小米 MiMo API Key（**仅云端模式需要**）——见 [获取免费的小米 MiMo API Key](#获取免费的小米-mimo-api-key)。*使用离线模式可跳过此项。*

## 快速开始

**下载项目**（任选一种）：

- **方式一（推荐，免装 Git）**：打开 <https://github.com/DJKING792/PhoneMic>，点击绿色 **Code** 按钮 → **Download ZIP**，解压到任意文件夹，进入解压出的 `PhoneMic` 文件夹。
- **方式二（开发者）**：打开 cmd 执行以下命令，然后进入下载好的 `PhoneMic` 文件夹。

  ```
  git clone https://github.com/DJKING792/PhoneMic.git
  ```

> 本机需已安装 **Python 3.10+**（如未安装，可从 <https://www.python.org> 下载，安装时务必勾选「Add python.exe to PATH」）。其余依赖首次运行会自动安装。

### Windows

1. **首次放行防火墙**：右键 `allow_firewall.bat` →「以管理员身份运行」（放行 8443 端口，只需一次）。若之后手机提示「已拒绝连接 / ERR_CONNECTION_REFUSED」，多半是这一步没做。
2. **双击 `start.bat` 启动**：首次会自动创建虚拟环境并安装依赖；随后让你选识别模式——`1` 云端（MiMo，会提示输入免费 Key，申请地址 <https://platform.xiaomimimo.com>）或 `2` 离线（本地 faster-whisper，免 Key）。选择写入 `.env`，下次自动沿用。
3. 屏幕显示「手机访问地址」（如 `https://192.168.x.x:8443`）和二维码。
4. 按手机系统完成连接（见下方「手机连接」），把电脑光标放到要输入的位置（记事本 / 微信 / 浏览器等），手机说话即可自动输入

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

   若要改用**离线模式**，把最后两行换成：

```bash
pip install faster-whisper
export PHONEMIC_ASR=local
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

iOS 对自签证书较严格，需手动信任，步骤如下：

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

## 获取免费的小米 MiMo API Key

云端模式需要一个免费的小米 MiMo API Key，3 步即可拿到：

<details>
<summary>📌 点击展开：3 步图文获取免费 MiMo API Key</summary>

**第 1 步 —— 注册 / 登录**

1. 浏览器打开 <https://platform.xiaomimimo.com>。
2. 点击右上角「登录 / Sign in」用小米账号登录；没有账号就点「注册 / Register」免费注册一个。

![第 1 步 —— 注册 / 登录 platform.xiaomimimo.com](assets/mimo-key/mimo-step1-register.png)

**第 2 步 —— 进入密钥管理页**

1. 登录后进入「控制台 / Console」（通常在右上角头像菜单）。
2. 在左侧边栏找到「API 密钥 / API Keys」（或「开放平台 → 密钥管理」）。
3. 这里会列出你名下的密钥（一开始为空）。

![第 2 步 —— 进入密钥管理页](assets/mimo-key/mimo-step2-keys.png)

**第 3 步 —— 创建并复制 Key**

1. 点击「创建密钥 / Create key」（或「+ 新建」）。
2. 随便起个名字（如 `PhoneMic`）并确认。
3. **立刻复制 Key**——它只显示一次。把它粘到你的 `.env` 里写成 `MIMO_API_KEY=你的key`；或者在 Windows 上直接运行 `start.bat`，在提示时粘贴即可。

![第 3 步 —— 创建并复制 Key](assets/mimo-key/mimo-step3-create.png)

> 💡 MiMo API 对个人使用有免费额度。请保管好你的 Key，不要提交到仓库（PhoneMic 的 `.gitignore` 已屏蔽 `.env`）。

</details>

## 安全说明

- 监听 `0.0.0.0:8443` 且默认不加鉴权——刻意设计，仅限**可信局域网**使用。
- API key 只在本地 `.env`（已被 `.gitignore` 屏蔽），证书为本地自签，均不上传仓库。
- **离线模式**下音频全程不出本机，识别完全本地完成。

## 常见问题

**Q：延迟大概多少毫秒？**
A：**云端模式**下，一段普通语句（一两句话）端到端约 **1–2 秒**——手机采集 + 局域网上传 + MiMo 识别 + 粘贴。 **离线模式**取决于模型大小与硬件：CPU 上 `small` 模型通常每段几百毫秒到约 1–2 秒；用 GPU 或 `tiny`/`base` 模型会更快。

**Q：支持多长的语音？**
A：没有硬性上限，但每次「按住说话」是一段录音。为兼顾识别准确率与延迟，建议单段控制在**几十秒到两三分钟**；长文稿拆成多段短录音效果更好，文字会持续流入光标。

**Q：断网能用吗？**
A：**云端模式**需要联网（调用 MiMo 的 ASR 接口），但你的**音频只会经自己的局域网传到本机电脑**，不经过任何第三方中转。若要做到**完全不联网**，请开启**离线模式**（`PHONEMIC_ASR=local`）：识别全程在本机运行，彻底离线可用。

**Q：我的语音隐私有保障吗？**
A：云端模式下，音频仅在局域网之外送往小米 ASR 接口做转写，PhoneMic 不存储任何内容；离线模式下音频则完全不出本机。

**Q：手机连不上 / 提示「已拒绝连接」？**
A：启动时会打印详细诊断信息（IP / ffmpeg / 证书 / 端口 / key 状态），连接问题看这里即可；电脑端 `https://localhost:8443/desktop` 还有实时连接状态页。多数「已拒绝连接」是防火墙拦截了 8443 端口（见快速开始）。

## 许可证

[MIT](LICENSE) © PhoneMic 贡献者。

## 贡献与支持

- 想参与开发？请看 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 发现安全漏洞？请遵循 [SECURITY.md](SECURITY.md)。
- 需要帮助？查看 [SUPPORT.md](SUPPORT.md)。
