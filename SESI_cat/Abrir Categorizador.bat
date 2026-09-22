@echo off
rem Abre o Categorizador ja no projeto SESI (o programa fica em _laterais\categorizador).
set "CATEGORIZADOR_PROJETO=sesi"
call "%~dp0..\_laterais\categorizador\iniciar.bat"
