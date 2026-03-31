@echo off
cd /d "%~dp0"

echo Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo Instalando dependencias...
uv sync

echo Compilando TurboAtalho...
uv run pyinstaller build.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO na compilacao! Verifique as mensagens acima.
    pause
    exit /b 1
)

echo.
echo Compilacao concluida! O executavel esta em: dist\TurboAtalho.exe
pause
