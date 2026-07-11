@echo off
REM build.bat — Compila Second Brain AI como ejecutable de Windows.
REM Ejecutar dentro de la carpeta del proyecto, en Windows, con Python 3.10/3.11 (64 bits).

echo ============================================
echo   Second Brain AI - build de ejecutable
echo ============================================

python -m venv venv_build
call venv_build\Scripts\activate.bat

echo.
echo [1/3] Instalando dependencias del proyecto...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [2/3] Instalando PyInstaller...
pip install pyinstaller

echo.
echo [3/3] Compilando con PyInstaller (esto puede tardar varios minutos)...
pyinstaller build_exe.spec --noconfirm

echo.
echo ============================================
echo Listo. El ejecutable esta en:
echo   dist\Second Brain AI\Second Brain AI.exe
echo ============================================
pause
