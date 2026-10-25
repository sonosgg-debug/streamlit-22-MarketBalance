@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Market Balance Dashboard

echo ===================================================
echo   Market Balance : Valuation ^& Balance Dashboard
echo ===================================================
echo.

REM 1. Streamlit 온보딩 이메일 프롬프트 및 전역 파일 권한 충돌 완벽 방어
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if not exist "%~dp0.streamlit_home" mkdir "%~dp0.streamlit_home"
set USERPROFILE=%~dp0.streamlit_home
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"
)

echo [알림] Streamlit 대시보드를 시작합니다...
echo [알림] 서버 구동이 완료되면 브라우저가 자동으로 열립니다.
echo.
echo - 접속 주소: http://localhost:8501
echo - 앱을 종료하려면 이 창을 닫거나 [Ctrl + C]를 누르세요.
echo ---------------------------------------------------
echo.

python -m streamlit run app.py --server.headless false %*

if errorlevel 1 (
    echo.
    echo [오류] 앱 실행 중 문제가 발생했습니다.
    echo.
    pause
)
