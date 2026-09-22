@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Categorizador de respostas abertas

rem ---- ambiente Python proprio (fora do OneDrive, para nao sincronizar milhares de arquivos)
set "VENV=%LOCALAPPDATA%\Categorizador\venv"
set "VPY=%VENV%\Scripts\python.exe"

if exist "%VPY%" goto :dependencias

echo Preparando o Categorizador pela primeira vez (leva de 1 a 3 minutos)...
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto :sem_python
%PY% -m venv "%VENV%"
if errorlevel 1 goto :erro

:dependencias
fc /b requirements.txt "%VENV%\requirements.ok" >nul 2>&1
if not errorlevel 1 goto :rodar
echo Instalando/atualizando os pacotes necessarios...
"%VPY%" -m pip install --disable-pip-version-check -q --upgrade pip >nul 2>&1
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :erro
copy /y requirements.txt "%VENV%\requirements.ok" >nul

:rodar
echo.
echo Abrindo o Categorizador no navegador...
echo (deixe esta janela aberta enquanto usa o programa; para encerrar, feche-a)
echo.
"%VPY%" app.py
if errorlevel 1 goto :erro
exit /b 0

:sem_python
echo.
echo O Python nao esta instalado neste computador.
where winget >nul 2>&1
if errorlevel 1 goto :sem_winget
choice /m "Deseja instalar o Python agora"
if errorlevel 2 goto :sem_winget
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo Python instalado. Feche esta janela e de dois cliques de novo no atalho do Categorizador.
pause
exit /b 0

:sem_winget
echo Baixe e instale o Python em https://www.python.org/downloads/
echo (na instalacao, marque "Add python.exe to PATH") e depois abra o Categorizador de novo.
start "" https://www.python.org/downloads/
pause
exit /b 1

:erro
echo.
echo Algo deu errado (veja a mensagem acima). Se o problema continuar, apague a pasta
echo   %VENV%
echo e abra o Categorizador de novo para reinstalar os pacotes.
pause
exit /b 1
