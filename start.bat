@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul
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
REM --- 识别模式选择（云端 / 离线）---
set "ASRMODE=cloud"
if defined TYPOMIC_ASR (
    if /i "%TYPOMIC_ASR%"=="local" set "ASRMODE=whisper"
    if /i "%TYPOMIC_ASR%"=="whisper" set "ASRMODE=whisper"
    if /i "%TYPOMIC_ASR%"=="sensevoice" set "ASRMODE=sensevoice"
) else if exist "%KEYFILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "TYPOMIC_ASR" "%KEYFILE%"`) do (
        if /i "%%B"=="local" set "ASRMODE=whisper"
        if /i "%%B"=="whisper" set "ASRMODE=whisper"
        if /i "%%B"=="sensevoice" set "ASRMODE=sensevoice"
    )
)
echo.
echo ============================================================
echo  请选择语音识别模式：
echo    1. 云端 MiMo（推荐）
echo       中文最强，需联网，免费申请 API key
echo    2. 本地 Whisper
echo       纯离线，英文好、中文一般，无标点
echo    3. 本地 SenseVoice（阿里开源模型，1G文件大小，下载需等待）
echo       纯离线，中文准，自带标点，CPU 可跑
echo  当前默认：!ASRMODE!
echo ============================================================
set /p "CHOICE=输入 1 / 2 / 3（直接回车沿用当前默认）："
if "!CHOICE!"=="2" (
    set "ASRMODE=whisper"
    set "TYPOMIC_ASR=whisper"
    REM 写入 .env 以便下次自动沿用（已存在则不再重复写入）
    findstr /b /i "TYPOMIC_ASR" "%KEYFILE%" >nul 2>&1
    if errorlevel 1 (
        >> "%KEYFILE%" echo TYPOMIC_ASR=whisper
    )
    echo 已选择离线模式（faster-whisper，已写入 .env，下次自动沿用）。
) else if "!CHOICE!"=="3" (
    set "ASRMODE=sensevoice"
    set "TYPOMIC_ASR=sensevoice"
    findstr /b /i "TYPOMIC_ASR" "%KEYFILE%" >nul 2>&1
    if errorlevel 1 (
        >> "%KEYFILE%" echo TYPOMIC_ASR=sensevoice
    )
    echo 已选择离线模式（SenseVoice，已写入 .env，下次自动沿用）。
) else (
    if not "!ASRMODE!"=="cloud" (
        set "TYPOMIC_ASR=!ASRMODE!"
        echo 沿用 .env 中的!ASRMODE!模式。
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
if "!ASRMODE!"=="whisper" (
    echo 正在安装本地 Whisper 依赖（faster-whisper，首次运行会下载模型权重）...
    "%VENV%\Scripts\python.exe" -m pip install -r "%BASE%requirements-whisper.txt"
    if errorlevel 1 (
        echo 离线依赖安装失败。请检查网络后重试，或改用云端模式。
        pause
        exit /b 1
    )
)
if "!ASRMODE!"=="sensevoice" (
    echo 正在安装 SenseVoice 依赖（torch/funasr/modelscope，首次下载模型）...
    "%VENV%\Scripts\python.exe" -m pip install -r "%BASE%requirements-sensevoice.txt"
    if errorlevel 1 (
        echo 离线依赖安装失败（torch/funasr/modelscope）。
        echo 请检查网络后重试，或改用云端模式。
        pause
        exit /b 1
    )
    goto :sv_predl
)
goto :aftersv

:sv_predl
REM 模型下载到 TypMic/models/SenseVoiceSmall（按模型名独立文件夹）
set "MS_CACHE=%BASE%models\SenseVoiceSmall"
if not exist "!MS_CACHE!" mkdir "!MS_CACHE!" 2>nul
set "MODELSCOPE_CACHE=!MS_CACHE!"
echo 模型将保存到：!MS_CACHE!（首次下载约 1GB，请耐心等待进度条）
echo 正在预下载 SenseVoice 模型...
    "%VENV%\Scripts\python.exe" -c "from funasr import AutoModel; AutoModel(model='iic/SenseVoiceSmall', trust_remote_code=True); print('SenseVoice model ready')"
:aftersv
REM --- MiMo API key（离线模式无需）---
if not "!ASRMODE!"=="cloud" (
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

REM ============================================================
REM --- AI 润色（仅云端模式可用，自动复用 MiMo key）---
REM ============================================================
if not "!ASRMODE!"=="cloud" (
    echo.
    echo 离线模式无需 key，AI 润色不可用，已保持关闭。
    call :setenv TYPOMIC_POLISH off
) else (
    set "CURPOLISH=off"
    set "CURMODE="
    if exist "%KEYFILE%" (
        for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "TYPOMIC_POLISH=" "%KEYFILE%"`) do set "CURPOLISH=%%B"
        for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "TYPOMIC_POLISH_MODE=" "%KEYFILE%"`) do set "CURMODE=%%B"
    )
    REM 本地引擎无需 key，AI 润色不可用（云端/本地模型已原生标点）
    if "!CURPOLISH!"=="on" if not defined CURMODE set "CURMODE=full"
    echo.
    echo ============================================================
    echo  AI 润色（复用 MiMo key；模型已原生标点，无需额外补标点）
    echo    1. 关闭         （纯识别，最快，自动标点符号）
    echo    2. 通用润色      （去口语+顺句+分段，默认风格）
    echo    3. 理顺逻辑      （适合说话散乱：补连接、理清层次）
    echo    4. 小说创作      （保留文学性/口语感，不强行规范化）
    echo    5. 公司文案      （商务正式、专业、结构清晰）
    echo    6. 行政公文      （公文规范、条理、庄重）
    echo  当前：!CURPOLISH!  !CURMODE!
    echo  默认推荐：1（关闭）。回车即采用默认。
    echo ============================================================
    set /p "PCHOICE=输入 1/2/3/4/5/6（回车=默认推荐）："
    if "!PCHOICE!"=="1" (
        call :setenv TYPOMIC_POLISH off
        echo 已选择：关闭 AI 润色。
    ) else if "!PCHOICE!"=="2" (
        call :setenv TYPOMIC_POLISH on
        call :setenv TYPOMIC_POLISH_MODE full
        echo 已选择：通用润色。
    ) else if "!PCHOICE!"=="3" (
        call :setenv TYPOMIC_POLISH on
        call :setenv TYPOMIC_POLISH_MODE logic
        echo 已选择：理顺逻辑。
    ) else if "!PCHOICE!"=="4" (
        call :setenv TYPOMIC_POLISH on
        call :setenv TYPOMIC_POLISH_MODE novel
        echo 已选择：小说创作。
    ) else if "!PCHOICE!"=="5" (
        call :setenv TYPOMIC_POLISH on
        call :setenv TYPOMIC_POLISH_MODE business
        echo 已选择：公司文案。
    ) else if "!PCHOICE!"=="6" (
        call :setenv TYPOMIC_POLISH on
        call :setenv TYPOMIC_POLISH_MODE admin
        echo 已选择：行政公文。
    ) else (
        call :setenv TYPOMIC_POLISH off
        echo 已选择：关闭 AI 润色（默认推荐）。
    )
)

REM --- 术语表（纯本地，无需 key）---
set "GLOSSARY_STATE=无"
if exist "%BASE%glossary.txt" set "GLOSSARY_STATE=已开启"
echo.
echo ============================================================
echo  术语表（错词纠正，纯本地无需 key）
echo    1. 关闭
echo    2. 开启（推荐：自动创建 glossary.txt，纠正常见谐音错词）
echo  当前：!GLOSSARY_STATE!
echo  默认推荐：2（开启）。回车即采用默认。
echo ============================================================
set /p "GCHOICE=输入 1/2（回车=默认推荐）："
if "!GCHOICE!"=="1" (
    call :setenv TYPOMIC_GLOSSARY off
    echo 已选择：关闭术语表。
) else (
    call :setenv TYPOMIC_GLOSSARY on
    if not exist "%BASE%glossary.txt" (
        if exist "%BASE%glossary.txt.example" (
            copy /y "%BASE%glossary.txt.example" "%BASE%glossary.txt" >nul
            echo 已从示例创建 glossary.txt（可随时编辑）。
        ) else (
            echo 未找到 glossary.txt.example，跳过。
        )
    ) else (
        echo glossary.txt 已存在，保持不变。
    )
)

echo.
echo ============================================================
echo  是否将根证书加入 Windows 信任（消除浏览器"不安全"警告）
echo    1. 不安装（默认，功能完全正常，仅浏览器提示"不安全"）
echo    2. 安装（会弹 UAC 提权，需管理员同意；Chrome/Edge 即变绿锁）
echo  说明：装不装都不影响任何功能，仅决定浏览器是否报警告。
echo ============================================================
set /p "CCHOICE=输入 1/2（回车=不安装）："
if "!CCHOICE!"=="2" (
  if not exist "%BASE%rootCA.pem" (
    echo 正在生成证书（首次运行）...
    call :gencert
  )
  echo 正在请求管理员权限安装根证书...
  powershell -Command "Start-Process -FilePath '%~dp0trust_cert.bat' -Verb RunAs" >nul 2>&1
  echo 若弹出 UAC 请点"是"；安装完成后该窗口会自动关闭。
)
goto :aftercert

:gencert
call "%VENV%\Scripts\python.exe" -c "import voice_input_server; voice_input_server.ensure_certs()" >nul 2>&1
goto :eof

:aftercert

REM Start server
echo [3/3] 正在启动服务...
echo 下方出现横幅即表示服务已启动，请保持此窗口打开。
echo 启动后请在电脑浏览器打开： https://localhost:8443/desktop
echo.
"%VENV%\Scripts\python.exe" "%BASE%voice_input_server.py"
echo.
echo 服务已停止。按任意键关闭。
pause

goto :eof

:setenv
set "K=%~1"
set "V=%~2"
if not exist "%KEYFILE%" ( type nul > "%KEYFILE%" )
findstr /v /b /i "%K%=" "%KEYFILE%" > "%KEYFILE%.tmp"
if exist "%KEYFILE%.tmp" ( move /y "%KEYFILE%.tmp" "%KEYFILE%" >nul )
>> "%KEYFILE%" echo %K%=%V%
goto :eof


