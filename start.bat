@echo off
setlocal enabledelayedexpansion
set "BASE=%~dp0"
set "VENV=%BASE%.venv"
set "KEYFILE=%BASE%.env"
set "PYTHON="

REM 查找可用的 Python（仅用绝对路径，不依赖 PATH 环境变量）
set "CAND=C:\Python314\python.exe C:\Python313\python.exe C:\Python312\python.exe C:\Users\Ax\.workbuddy\binaries\python\versions\3.13.12\python.exe"
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

REM 安装依赖（轻量，已安装的会跳过）
echo [2/3] 正在安装依赖（无需下载模型，很快）...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r "%BASE%requirements.txt"
if errorlevel 1 (
    echo 依赖安装失败。请检查网络连接后重试。
    pause
    exit /b 1
)

REM --- MiMo API key：仅提示一次，随后自动写入 .env ---
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
    echo  可免费申请：https://mimo.mi.com，注册后创建 API key。
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

REM Start server
echo [3/3] 正在启动服务...
echo 下方出现横幅即表示服务已启动，请保持此窗口打开。
echo.
"%VENV%\Scripts\python.exe" "%BASE%voice_input_server.py"
echo.
echo 服务已停止。按任意键关闭。
pause
