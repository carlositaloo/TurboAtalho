# -*- mode: python ; coding: utf-8 -*-
# build.spec — PyInstaller spec para Turbo Atalho
# Compilar com:  pyinstaller build.spec

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('img', 'img')],
    hiddenimports=['keyboard', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtSql',
        'PySide6.QtOpenGL', 'PySide6.QtPdf', 'PySide6.QtWebEngineCore', 'PySide6.QtMultimedia',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TurboAtalho',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/icon.ico',
    # Sem admin: a prioridade dos jogos pede UAC só na hora de salvar,
    # e "Iniciar com o Windows" não funciona com apps que exigem admin.
    uac_admin=False,
)
