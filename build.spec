# -*- mode: python ; coding: utf-8 -*-
# build.spec — PyInstaller spec para Turbo Atalho
# Compilar com:  pyinstaller build.spec

import os
import customtkinter

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('img', 'img'),
        (os.path.dirname(customtkinter.__file__), 'customtkinter'),
    ],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pystray._win32',
        'keyboard',
        'psutil',
        'pyperclip',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/icon.ico',
    uac_admin=True,
)
