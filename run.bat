@echo off
setlocal
cd /d "%~dp0"

echo ================================================================
echo   Sistem Informasi E-Posyandu Terintegrasi
echo   Posyandu Lestari 12 - Merden, Purwanegara, Banjarnegara
echo ================================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [GALAT] Python tidak ditemukan di PATH.
    echo         Pasang Python dari https://www.python.org/downloads/
    echo         lalu centang "Add Python to PATH" saat instalasi.
    echo.
    pause
    exit /b 1
)

python -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Flask belum terpasang. Memasang sekarang...
    python -m pip install flask
    echo.
)

if not exist "data\eposyandu.db" (
    echo [INFO] Basis data belum ada - akan dibuat otomatis saat server mulai.
    echo.
)

echo Membuka http://127.0.0.1:5000 di peramban (tunggu 3 detik)...
echo Tekan CTRL+C atau tutup jendela ini untuk menghentikan server.
echo.

rem Buka peramban setelah jeda ~3 detik, sementara server jalan di jendela ini.
rem Dipakai "ping" (bukan "timeout") karena ping tidak butuh input keyboard,
rem dan "explorer" agar tidak perlu kutip bersarang untuk membuka peramban.
start /b cmd /c "ping -n 4 127.0.0.1 >nul & explorer http://127.0.0.1:5000"

python app.py

echo.
echo Server telah dihentikan.
pause
endlocal
