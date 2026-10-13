@echo off
rem Abre o Tabulador no projeto SESI
set "TABULADOR_PROJETO=sesi"
if exist "%~dp0iniciar.bat" (
    call "%~dp0iniciar.bat"
    exit /b %errorlevel%
)
if exist "%~dp0..\_laterais\tabulador\iniciar.bat" (
    call "%~dp0..\_laterais\tabulador\iniciar.bat"
    exit /b %errorlevel%
)
if exist "%~dp0..\tabulador\iniciar.bat" (
    call "%~dp0..\tabulador\iniciar.bat"
    exit /b %errorlevel%
)
echo Nao foi possivel encontrar o iniciar.bat
pause
