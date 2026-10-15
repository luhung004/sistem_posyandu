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

python -c "import flask, waitress" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Memasang dependensi aplikasi...
    python -m pip install -r requirements.txt
    echo.
)

rem Kunci penandatangan cookie sesi harus sama dari satu kali jalan ke
rem berikutnya, jadi disimpan di berkas lokal yang tidak ikut terunggah.
if not exist ".secret_key" (
    echo [INFO] Membuat kunci rahasia untuk sesi...
    python -c "import secrets; open('.secret_key','w').write(secrets.token_hex(32))"
)
set "EPOSYANDU_SECRET="
for /f "usebackq delims=" %%k in (".secret_key") do set "EPOSYANDU_SECRET=%%k"

rem Cookie berflag Secure tidak terkirim lewat http://127.0.0.1, jadi untuk
rem pemakaian lokal nilainya dimatikan.
set "EPOSYANDU_HTTPS=0"
set "PORT=5000"

rem Buat basis data beserta data contoh bila belum ada.
python -c "import db; db.init_db(seed=True) if not db.tabel_ada() else None"
if exist "data\demo-credentials.txt" (
    echo.
    echo [PENTING] Kredensial demo tersimpan di data\demo-credentials.txt
    echo            Buka berkas itu untuk melihat nama pengguna dan kata sandi.
    echo.
)

echo Membuka http://127.0.0.1:%PORT% di peramban (tunggu 3 detik)...
echo Tekan CTRL+C atau tutup jendela ini untuk menghentikan server.
echo.

start /b cmd /c "ping -n 4 127.0.0.1 >nul & explorer http://127.0.0.1:%PORT%"

waitress-serve --host=127.0.0.1 --port=%PORT% wsgi:application

echo.
echo Server telah dihentikan.
pause
endlocal