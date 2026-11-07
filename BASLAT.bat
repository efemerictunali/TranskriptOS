@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Canli Turkce Transkript

rem ---- Uygun Python'u bul (3.10 - 3.13) ----
set "PY="
py -3.12 -c "" >nul 2>&1 && set "PY=py -3.12"
if not defined PY call :dene python
if not defined PY call :dene py
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not defined PY (
  echo Python bulunamadi, otomatik kuruluyor. Biraz bekle...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

%PY% --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python kurulamadi. python.org adresinden Python 3.12 kurup
  echo "Add Python to PATH" kutusunu isaretle, sonra bu dosyayi tekrar ac.
  pause
  exit /b
)

rem ---- Paketleri ilk seferde kur ----
if not exist ".kurulum_tamam" (
  echo Gerekli paketler kuruluyor, ilk seferde birkac dakika surer...
  %PY% -m pip install --upgrade pip
  %PY% -m pip install faster-whisper soundcard "numpy<2" "av<14"
  if errorlevel 1 (
    echo Paket kurulumunda hata olustu. Ekrandaki hatayi Claude'a gonder.
    pause
    exit /b
  )
  echo tamam> ".kurulum_tamam"
)

rem ---- Calistir ----
%PY% canli_transkript.py %*
echo.
echo Notlarin "notlar" klasorunde.
start "" "%~dp0notlar"
pause
exit /b

:dene
%1 -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>&1 && set "PY=%1"
exit /b
