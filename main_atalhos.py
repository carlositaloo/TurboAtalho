# main.py (atalhos & power manager)

import json
import os
import sys
import threading
import time
import subprocess
import psutil
import re
import ctypes

from pynput.keyboard import Key, KeyCode, Listener, Controller
from pystray            import Icon, MenuItem, Menu
from PIL                import Image

from defaults import DEFAULT_CONFIG

HERE         = os.path.dirname(__file__)
CONFIG_FILE  = os.path.join(HERE, 'config.json')
MON_INTERVAL = 2
DOUBLE_INT   = 0.5

# Se executado via PyInstaller --onefile, os recursos ficam em _MEIPASS
if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(__file__)

ICONS_DIR   = os.path.join(BASE, 'icons')
DEFAUT_FILE = os.path.join(BASE, 'defaults.json')

# Controller para enviar teclas
_kbd = Controller()

# Mapa de prioridades para psutil
PRIO_MAP = {
    "Normal": psutil.NORMAL_PRIORITY_CLASS,
    "High":   psutil.HIGH_PRIORITY_CLASS
}

# GUIDs de fallback (em minúsculas)
PLAN_FALLBACK = {
    "Desempenho máximo":    "e9a42b02-d5df-448d-aa00-03f14749eb61".lower(),
    "Alto desempenho":      "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c".lower(),
    "Equilibrado":          "381b4222-f694-41f0-9685-ff5bb260df2e".lower(),
    "Economia de energia":  "a1841308-3541-4fab-bc81-f71556f20b4a".lower()
}

# Flag para criar nova janela de console no Windows
if sys.platform == "win32":
    CREATE_NEW_CONSOLE = subprocess.CREATE_NEW_CONSOLE
else:
    CREATE_NEW_CONSOLE = 0


def get_plan_guids():
    """Retorna dict: nome_plano → guid_lowercase disponíveis no sistema."""
    try:
        result = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        return {}
    mapping = {}
    for line in result.stdout.splitlines():
        m = re.search(r"GUID:\s*([0-9A-Fa-f-]+)\s*\((.+?)\)", line)
        if m:
            mapping[m.group(2).strip()] = m.group(1).lower()
    return mapping


def get_active_window_title():
    """Retorna o título da janela atualmente ativa no Windows."""
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def executar_comando(cmd):
    """
    Se for executável (.exe), abre em nova janela de console no Windows;
    senão executa no shell.
    """
    if os.path.isfile(cmd) or cmd.lower().endswith('.exe'):
        subprocess.Popen([cmd], creationflags=CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(cmd, shell=True)


class AtalhosListener:
    def __init__(self):
        cfg = load_config()
        self.atalhos = cfg["atalhos"]
        self.enable_calc_percent = cfg.get("enable_calc_percent", True)
        self.mtime   = os.path.getmtime(CONFIG_FILE)
        self.last    = {}

    def reload_if_needed(self):
        m = os.path.getmtime(CONFIG_FILE)
        if m != self.mtime:
            cfg = load_config()
            self.atalhos           = cfg["atalhos"]
            self.enable_calc_percent = cfg.get("enable_calc_percent", True)
            self.mtime   = m

    def on_press(self, key):
        # --- Caso especial (configurável): shift direito na Calculadora envia '%' ---
        if self.enable_calc_percent \
           and key == Key.shift_r \
           and get_active_window_title() == "Calculadora":
            _kbd.press(Key.shift)
            _kbd.press('5')
            _kbd.release('5')
            _kbd.release(Key.shift)
            return

        # --- Atalhos configuráveis (duplo-pressionar) ---
        self.reload_if_needed()
        now = time.time()
        for a in self.atalhos:
            try:
                tecla = eval(a['tecla'])
            except:
                tecla = a['tecla']
            match = (
                key == tecla or
                (isinstance(key, KeyCode) and getattr(key, 'char', None) == tecla)
            )
            if not match:
                continue
            prev = self.last.get(a['tecla'])
            if prev and (now - prev) < DOUBLE_INT:
                executar_comando(a['comando'])
                self.last[a['tecla']] = None
            else:
                self.last[a['tecla']] = now

    def start(self):
        Listener(on_press=self.on_press).start()


class PowerManager:
    def __init__(self):
        cfg          = load_config()
        self.mon_cfg = cfg["monitores"]
        self.mtime   = os.path.getmtime(CONFIG_FILE)
        self.plan_map = get_plan_guids()
        self.state   = {m['process'].lower(): False for m in self.mon_cfg}

    def reload_if_needed(self):
        m = os.path.getmtime(CONFIG_FILE)
        if m != self.mtime:
            cfg          = load_config()
            self.mon_cfg = cfg["monitores"]
            self.mtime   = m
            self.plan_map= get_plan_guids()
            self.state   = {m['process'].lower(): False for m in self.mon_cfg}

    def monitor(self):
        while True:
            self.reload_if_needed()
            for m in self.mon_cfg:
                pname = m['process'].lower()
                procs = [
                    p for p in psutil.process_iter(['name'])
                    if p.info['name'] and p.info['name'].lower().startswith(pname)
                ]
                active = bool(procs)

                guid_on  = self.plan_map.get(m['power_on'], PLAN_FALLBACK.get(m['power_on']))
                guid_off = self.plan_map.get(m['power_off'], PLAN_FALLBACK.get(m['power_off']))

                if not guid_on:
                    guid_on = PLAN_FALLBACK["Alto desempenho"]
                if not guid_off:
                    guid_off = PLAN_FALLBACK["Equilibrado"]

                if active and not self.state[pname]:
                    try:
                        subprocess.run(["powercfg", "-setactive", guid_on], check=True)
                    except subprocess.CalledProcessError:
                        pass
                    for p in procs:
                        try:
                            p.nice(PRIO_MAP.get(m['priority'], psutil.NORMAL_PRIORITY_CLASS))
                        except:
                            pass
                    self.state[pname] = True

                elif not active and self.state[pname]:
                    try:
                        subprocess.run(["powercfg", "-setactive", guid_off], check=True)
                    except subprocess.CalledProcessError:
                        pass
                    self.state[pname] = False

            time.sleep(MON_INTERVAL)


def abrir_config(icon, item):
    exe = os.path.join(HERE, 'gui_configurator.exe')
    py  = os.path.join(HERE, 'gui_configurator.py')
    args = [exe] if os.path.exists(exe) else [sys.executable, py]
    subprocess.Popen(args)


def criar_tray():
    img  = Image.open(os.path.join(ICONS_DIR, 'icon.png'))
    menu = Menu(
        MenuItem('Opções', abrir_config),
        MenuItem('Sair',    lambda icon, item: icon.stop())
    )
    Icon('Atalhos', img, 'Atalhos', menu).run()

if __name__ == "__main__":
    threading.Thread(target=PowerManager().monitor, daemon=True).start()
    AtalhosListener().start()
    criar_tray()
