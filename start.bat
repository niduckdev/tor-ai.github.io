@echo off
chcp 65001 >nul
title TOR AI — Startup

echo.
echo ============================================
echo   TOR AI — เริ่มต้นระบบ
echo ============================================
echo.

:: ── ตรวจสอบ API Key ──
if "%TYPHOON_API_KEY%"=="" (
    set /p TYPHOON_API_KEY="กรอก TYPHOON_API_KEY (sk-...): "
)

if "%TYPHOON_API_KEY%"=="" (
    echo ❌ ไม่ได้กรอก API Key — ยกเลิก
    pause
    exit /b
)

echo ✅ API Key พร้อม
echo.

:: ── เปิด Backend ──
echo 🚀 กำลังเปิด Backend...
start "TOR Backend" cmd /k "set TYPHOON_API_KEY=%TYPHOON_API_KEY% && python D:\TOR_AI\Program\backend.py"

:: รอ Backend ขึ้น
timeout /t 3 /nobreak >nul

:: ── เปิด ngrok ──
echo 🌐 กำลังเปิด ngrok...
start "ngrok" cmd /k "ngrok http 8000"

echo.
echo ============================================
echo   ระบบเปิดแล้ว!
echo   - ดู ngrok URL ได้ที่หน้าต่าง ngrok
echo   - ส่ง URL ให้เพื่อนในทีมได้เลย
echo ============================================
echo.
pause
