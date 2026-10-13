@echo off
rem Abre o Tabulador (codigo unico em projetos\_laterais	abulador) direto no projeto SESI
set "TABULADOR_PROJETO=sesi"
if exist "%~dp0..\_laterais	abulador\iniciar.bat" (
    call "%~dp0..\_laterais	abulador\iniciar.bat"
    exit /b %errorlevel%
)
echo Nao foi possivel encontrar projetos\_laterais	abulador\iniciar.bat
pause
