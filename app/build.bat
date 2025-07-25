@echo off
echo ======================================
echo    Compilando TurboAtalho para EXE
echo ======================================

echo.
echo [1/4] Verificando dependencias...
pip install pyinstaller psutil pynput pystray pillow

echo.
echo [2/4] Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del "*.spec"

echo.
echo [3/4] Compilando aplicacao...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "TurboAtalho" ^
    --icon "icons/icon.ico" ^
    --add-data "icons;icons" ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "pkg_resources.py2_warn" ^
    --distpath "dist" ^
    turbo_atalho_modificado.py

echo.
echo [4/4] Finalizando...
if exist "dist\TurboAtalho.exe" (
    echo.
    echo ======================================
    echo    SUCESSO! Executavel criado em:
    echo    dist\TurboAtalho.exe
    echo ======================================
    echo.
    echo Pressione qualquer tecla para abrir a pasta...
    pause > nul
    explorer dist
) else (
    echo.
    echo ======================================
    echo    ERRO! Falha na compilacao.
    echo    Verifique as mensagens de erro acima.
    echo ======================================
    echo.
    pause
)