@echo off
echo ==========================================
echo    KasirKu - Sistem Kasir Native
echo ==========================================
echo.
echo Mengecek Python...
python --version
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan!
    echo Silakan install Python 3.10+ dari python.org
    pause
    exit /b 1
)

echo.
echo Menginstall dependencies...
pip install -r requirements.txt

echo.
echo ==========================================
echo Menjalankan KasirKu...
echo ==========================================
python main.py

pause
