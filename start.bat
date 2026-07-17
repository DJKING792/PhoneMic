@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set "BASE=%~dp0"
set "VENV=%BASE%.venv"
set "KEYFILE=%BASE%.env"
set "PYTHON="
REM 查找可用的 Python（仅用绝对路径，不依赖 PATH 环境变量）
set "CAND=C:\Python314\python.exe C:\Python313\python.exe C:\Python312\python.exe"
set "CAND=%CAND% C:\Users\Ax\.workbuddy\binaries\python\versions\3.13.12\python.exe"
for %%i in (%CAND%) do (
    if not defined PYTHON (
        if exist "%%i" set "PYTHON=%%i"
    )
)
if not defined PYTHON (
    for %%i in (python python3) do (
        set "P=%%~$PATH:i"
        if defined P if not defined PYTHON set "PYTHON=!P!"
    )
)
if not defined PYTHON (
    echo 错误：未找到 Python。请安装 Python 3.10+ 或将其加入 PATH。
    pause
    exit /b 1
)
echo 正在使用 Python：%PYTHON%
REM 若虚拟环境不存在则创建
if not exist "%VENV%\Scripts\python.exe" (
    echo [1/3] 正在创建虚拟环境...
    "%PYTHON%" -m venv "%VENV%"
)
REM --- 识别模式选择（云端 / 离线）---
set "ASRMODE=cloud"
if defined TYPOMIC_ASR (
    if /i "%TYPOMIC_ASR%"=="local" set "ASRMODE=local"
) else if exist "%KEYFILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "TYPOMIC_ASR" "%KEYFILE%"`) do (
        if /i "%%B"=="local" set "ASRMODE=local"
    )
)
echo.
echo ============================================================
echo  请选择语音识别模式：
echo    1. 云端模式（小米 MiMo）
echo       中文 / 方言强，需免费 API key
echo    2. 离线模式（本地 faster-whisper）
echo       无需 key，可完全不联网
echo  当前默认：!ASRMODE!
echo ============================================================
set /p "CHOICE=输入 1 或 2（直接回车沿用当前默认）："
if "!CHOICE!"=="2" (
    set "ASRMODE=local"
    set "TYPOMIC_ASR=local"
    REM 写入 .env 以便下次自动沿用（已存在则不再重复写入）
    findstr /b /i "TYPOMIC_ASR" "%KEYFILE%" >nul 2>&1
    if errorlevel 1 (
        >> "%KEYFILE%" echo TYPOMIC_ASR=local
    )
    echo 已选择离线模式（已写入 .env，下次自动沿用）。
) else (
    if "!ASRMODE!"=="local" (
        set "TYPOMIC_ASR=local"
        echo 沿用 .env 中的离线模式。
    ) else (
        echo 使用云端模式。
    )
)
REM 安装依赖（轻量，已安装的会跳过）
echo [2/3] 正在安装依赖（无需下载模型，很快）...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r "%BASE%requirements.txt"
if errorlevel 1 (
    echo 依赖安装失败。请检查网络连接后重试。
    pause
    exit /b 1
)
if "!ASRMODE!"=="local" (
    echo 正在安装离线识别依赖（faster-whisper，首次运行会下载模型权重）...
    "%VENV%\Scripts\python.exe" -m pip install -r "%BASE%requirements-offline.txt"
    if errorlevel 1 (
        echo 离线依赖安装失败。请检查网络后重试，或改用云端模式。
        pause
        exit /b 1
    )
)
REM --- MiMo API key（离线模式无需）---
if "!ASRMODE!"=="local" (
    echo 离线模式：无需 MiMo API key。
    goto :afterkey
)
set "HAVE_KEY="
if defined MIMO_API_KEY (
    if not "%MIMO_API_KEY%"=="" set "HAVE_KEY=1"
) else if exist "%KEYFILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "MIMO_API_KEY" "%KEYFILE%"`) do (
        if not "%%B"=="" set "HAVE_KEY=1"
    )
)
if not defined HAVE_KEY (
    echo.
    echo ============================================================
    echo  语音识别需要 MiMo API key。
    echo  可免费申请：https://platform.xiaomimimo.com，注册后创建 API key。
    echo ============================================================
    set /p "USERKEY=请输入你的 MiMo API key（留空则跳过）："
    if not "!USERKEY!"=="" (
        > "%KEYFILE%" echo MIMO_API_KEY=!USERKEY!
        set "MIMO_API_KEY=!USERKEY!"
        echo.
        echo API key 已保存到 .env
    ) else (
        echo.
        echo 未输入 key。服务仍会启动，但语音识别会失败。
        echo 请编辑 .env 或设置 MIMO_API_KEY 后重启。
    )
) else (
    echo MiMo API key：已配置
)
:afterkey
REM Start server
echo [3/3] 正在启动服务...
echo 下方出现横幅即表示服务已启动，请保持此窗口打开。
echo.
"%VENV%\Scripts\python.exe" "%BASE%voice_input_server.py"
echo.
echo 服务已停止。按任意键关闭。
pause
