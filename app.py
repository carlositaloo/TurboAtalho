# app.py - Unificado (atalhos, power manager, configurador GUI)

import json
import os
import sys
import threading
import time
import subprocess
import psutil
import re
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from pynput.keyboard import Key, KeyCode, Listener, Controller
from pystray import Icon, MenuItem, Menu
from PIL import Image

# --- Defaults.py ---
DEFAULT_CONFIG = {
    # Ativa ou desativa o atalho especial Shift‑Direito → '%' na Calculadora
    "enable_calc_percent": True,
    "atalhos": [
        {"tecla": "Key.num_lock", "comando": "calc.exe"},
        {"tecla": "Key.menu",     "comando": "notepad.exe"},
        {"tecla": "Key.home",     "comando": "powershell.exe"},
    ],
    "monitores": [
    ],
}

# --- Configuração de caminhos ---
HERE = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(HERE, 'config.json')
MON_INTERVAL = 2
DOUBLE_INT = 0.5

if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(__file__)

ICONS_DIR = os.path.join(BASE, 'icons')

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

if sys.platform == "win32":
    CREATE_NEW_CONSOLE = subprocess.CREATE_NEW_CONSOLE
else:
    CREATE_NEW_CONSOLE = 0

# --- Funções utilitárias ---

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

def load_config(default=DEFAULT_CONFIG):
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default.copy()
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def executar_comando(cmd):
    """
    Se for executável (.exe), abre em nova janela de console no Windows;
    senão executa no shell.
    """
    if os.path.isfile(cmd) or cmd.lower().endswith('.exe'):
        subprocess.Popen([cmd], creationflags=CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(cmd, shell=True)

# --- AtalhosListener ---

class AtalhosListener:
    def __init__(self):
        cfg = load_config()
        self.atalhos = cfg["atalhos"]
        self.enable_calc_percent = cfg.get("enable_calc_percent", True)
        self.mtime = os.path.getmtime(CONFIG_FILE)
        self.last = {}

    def reload_if_needed(self):
        m = os.path.getmtime(CONFIG_FILE)
        if m != self.mtime:
            cfg = load_config()
            self.atalhos = cfg["atalhos"]
            self.enable_calc_percent = cfg.get("enable_calc_percent", True)
            self.mtime = m

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

# --- PowerManager ---

class PowerManager:
    def __init__(self):
        cfg = load_config()
        self.mon_cfg = cfg["monitores"]
        self.mtime = os.path.getmtime(CONFIG_FILE)
        self.plan_map = get_plan_guids()
        self.state = {m['process'].lower(): False for m in self.mon_cfg}

    def reload_if_needed(self):
        m = os.path.getmtime(CONFIG_FILE)
        if m != self.mtime:
            cfg = load_config()
            self.mon_cfg = cfg["monitores"]
            self.mtime = m
            self.plan_map = get_plan_guids()
            self.state = {m['process'].lower(): False for m in self.mon_cfg}

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

                guid_on = self.plan_map.get(m['power_on'], PLAN_FALLBACK.get(m['power_on']))
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

# --- GUI Configurator ---

PRIO_DISPLAY = ["Normal", "Alta"]
PRIO_DISPLAY_TO_INTERNAL = {"Normal": "Normal", "Alta": "High"}
PRIO_INTERNAL_TO_DISPLAY = {v: k for k, v in PRIO_DISPLAY_TO_INTERNAL.items()}

POWER_DISPLAY = [
    "Desempenho máximo",
    "Alto desempenho",
    "Equilibrado",
    "Economia de energia"
]

class ConfiguratorUI(tk.Tk):
    PLACEHOLDER_TECLA = "Clique e pressione tecla"

    def __init__(self, default_config):
        super().__init__()

        # Ícone na janela / taskbar (somente .ico)
        ico_ico = os.path.join(os.path.dirname(__file__), 'icons', 'icon.ico')
        if os.path.exists(ico_ico):
            self.iconbitmap(ico_ico)

        # Dados e configurações
        self.config = load_config(default_config)
        self.atalhos = self.config["atalhos"]
        self.monitores = self.config["monitores"]
        self.enable_calc = tk.BooleanVar(value=self.config.get("enable_calc_percent", True))

        # Construção da GUI
        self.title("Configurar Atalhos & Energia")
        self.geometry("280x430")
        self.resizable(False, False)

        nb = ttk.Notebook(self)
        nb.place(x=0, y=0, width=280, height=380)
        self._build_shortcuts_tab(nb)
        self._build_monitors_tab(nb)

        ttk.Button(self, text="Fechar", command=self.destroy)\
            .place(x=200, y=395, width=70, height=28)

    def _build_shortcuts_tab(self, nb):
        tab = ttk.Frame(nb); nb.add(tab, text="Gerenciar Atalhos")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Tecla:")\
            .grid(row=0, column=0, sticky='w', padx=3, pady=2)
        self.entry_tecla = ttk.Entry(tab, width=20)
        self.entry_tecla.grid(row=0, column=1, columnspan=2, sticky='ew', padx=3, pady=2)
        self.entry_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.entry_tecla.bind("<FocusIn>", self._on_tecla_focus_in)
        self.entry_tecla.bind("<FocusOut>", self._on_tecla_focus_out)

        ttk.Label(tab, text="Comando:")\
            .grid(row=1, column=0, sticky='w', padx=3, pady=2)
        self.entry_cmd = ttk.Entry(tab, width=20)
        self.entry_cmd.grid(row=1, column=1, sticky='ew', padx=3, pady=2)
        ttk.Button(tab, text="…", width=2, command=self._browse_file)\
            .grid(row=1, column=2, padx=3, pady=2)

        ttk.Button(tab, text="Adicionar", command=self._add_shortcut)\
            .grid(row=2, column=0, padx=3, pady=4, sticky='w')
        ttk.Button(tab, text="Remover Selecionado", command=self._remove_shortcut)\
            .grid(row=2, column=1, padx=3, pady=4, sticky='w')

        # Checkbutton para o atalho especial na Calculadora
        chk = ttk.Checkbutton(
            tab,
            text="Ativar '%' na Calculadora (Shift‑Direito)",
            variable=self.enable_calc,
            command=self._on_toggle_calc
        )
        chk.grid(row=3, column=0, columnspan=3, sticky='w', padx=3, pady=4)

        self.lb_atalhos = tk.Listbox(tab, height=8)
        self.lb_atalhos.grid(row=4, column=0, columnspan=3, sticky='nsew', padx=3, pady=2)
        tab.rowconfigure(4, weight=1)
        self._refresh_shortcuts()

    def _build_monitors_tab(self, nb):
        tab = ttk.Frame(nb); nb.add(tab, text="Gerenciar Energia")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Processo:")\
            .grid(row=0, column=0, sticky='w', padx=3, pady=2)
        self.entry_proc = ttk.Entry(tab, width=16)
        self.entry_proc.grid(row=0, column=1, sticky='ew', padx=3, pady=2)

        ttk.Label(tab, text="Prioridade:")\
            .grid(row=1, column=0, sticky='w', padx=3, pady=2)
        self.combo_prio = ttk.Combobox(
            tab, values=PRIO_DISPLAY, width=14, state='readonly'
        )
        self.combo_prio.grid(row=1, column=1, sticky='ew', padx=3, pady=2)
        self.combo_prio.set(PRIO_DISPLAY[1])

        ttk.Label(tab, text="Plano ao Iniciar:")\
            .grid(row=2, column=0, sticky='w', padx=3, pady=2)
        self.combo_on = ttk.Combobox(
            tab, values=POWER_DISPLAY, width=14, state='readonly'
        )
        self.combo_on.grid(row=2, column=1, sticky='ew', padx=3, pady=2)
        self.combo_on.set(POWER_DISPLAY[1])

        ttk.Label(tab, text="Plano ao Parar:")\
            .grid(row=3, column=0, sticky='w', padx=3, pady=2)
        self.combo_off = ttk.Combobox(
            tab, values=POWER_DISPLAY, width=14, state='readonly'
        )
        self.combo_off.grid(row=3, column=1, sticky='ew', padx=3, pady=2)
        self.combo_off.set(POWER_DISPLAY[2] if len(POWER_DISPLAY) > 1 else POWER_DISPLAY[0])

        ttk.Button(tab, text="Adicionar", command=self._add_monitor)\
            .grid(row=4, column=0, padx=3, pady=4, sticky='w')
        ttk.Button(tab, text="Remover Selecionado", command=self._remove_monitor)\
            .grid(row=4, column=1, padx=3, pady=4, sticky='w')

        self.lb_mon = tk.Listbox(tab, height=8)
        self.lb_mon.grid(row=5, column=0, columnspan=3, sticky='nsew', padx=3, pady=2)
        tab.rowconfigure(5, weight=1)
        self._refresh_monitors()

    def _on_tecla_focus_in(self, _):
        if self.entry_tecla.get() == self.PLACEHOLDER_TECLA:
            self.entry_tecla.delete(0, tk.END)
            self.bind_all("<KeyPress>", self._on_key_capture)

    def _on_tecla_focus_out(self, _):
        if not self.entry_tecla.get():
            self.entry_tecla.insert(0, self.PLACEHOLDER_TECLA)

    def _on_key_capture(self, e):
        k = e.char if e.char and len(e.char) == 1 else f"Key.{e.keysym.lower()}"
        self.entry_tecla.delete(0, tk.END)
        self.entry_tecla.insert(0, k)
        self.unbind_all("<KeyPress>")

    def _refresh_shortcuts(self):
        self.lb_atalhos.delete(0, tk.END)
        for a in self.atalhos:
            self.lb_atalhos.insert(tk.END, f"{a['tecla']} → {a['comando']}")

    def _add_shortcut(self):
        t, c = self.entry_tecla.get().strip(), self.entry_cmd.get().strip()
        if not t or t.startswith("Clique") or not c:
            messagebox.showwarning("Atenção", "Defina tecla e comando válidos")
            return
        self.atalhos.append({"tecla": t, "comando": c})
        self.config["atalhos"] = self.atalhos
        save_config(self.config)
        self.entry_tecla.delete(0, tk.END)
        self.entry_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.entry_cmd.delete(0, tk.END)
        self._refresh_shortcuts()

    def _remove_shortcut(self):
        sel = self.lb_atalhos.curselection()
        if sel:
            del self.atalhos[sel[0]]
            self.config["atalhos"] = self.atalhos
            save_config(self.config)
            self._refresh_shortcuts()

    def _on_toggle_calc(self):
        self.config["enable_calc_percent"] = self.enable_calc.get()
        save_config(self.config)

    def _browse_file(self):
        p = filedialog.askopenfilename(
            title="Selecione executável",
            filetypes=[("Executáveis","*.exe"),("Todos","*.*")]
        )
        if p:
            p = os.path.normpath(p)
            self.entry_cmd.delete(0, tk.END)
            self.entry_cmd.insert(0, p)

    def _refresh_monitors(self):
        self.lb_mon.delete(0, tk.END)
        for m in self.monitores:
            disp = PRIO_INTERNAL_TO_DISPLAY.get(m['priority'], m['priority'])
            txt = f"{m['process']} | {disp} | On:{m['power_on']} | Off:{m['power_off']}"
            self.lb_mon.insert(tk.END, txt)

    def _add_monitor(self):
        p = self.entry_proc.get().strip()
        pr = self.combo_prio.get()
        pr_int = PRIO_DISPLAY_TO_INTERNAL[pr]
        on = self.combo_on.get()
        off = self.combo_off.get()
        if not p:
            messagebox.showwarning("Atenção", "Informe o nome do processo")
            return
        self.monitores.append({"process": p,
                               "priority": pr_int,
                               "power_on": on,
                               "power_off": off})
        self.config["monitores"] = self.monitores
        save_config(self.config)
        self.entry_proc.delete(0, tk.END)
        self._refresh_monitors()

    def _remove_monitor(self):
        sel = self.lb_mon.curselection()
        if sel:
            del self.monitores[sel[0]]
            self.config["monitores"] = self.monitores
            save_config(self.config)
            self._refresh_monitors()

# --- Tray e inicialização ---

def abrir_config(icon=None, item=None):
    # Abre a interface gráfica de configuração
    def _run():
        app = ConfiguratorUI(DEFAULT_CONFIG)
        app.mainloop()
    threading.Thread(target=_run, daemon=True).start()

def criar_tray():
    img = Image.open(os.path.join(ICONS_DIR, 'icon.png'))
    menu = Menu(
        MenuItem('Opções', abrir_config),
        MenuItem('Sair', lambda icon, item: icon.stop())
    )
    icon = Icon('Atalhos', img, 'Atalhos', menu)
    icon.run()

# --- Inicialização automática ---

def register_startup():
    """Registra este script para execução automática na inicialização do Windows."""
    if getattr(sys, 'frozen', False):
        # Executável empacotado com PyInstaller
        exe_path = sys.executable
    else:
        # Script Python normal
        script_path = os.path.abspath(__file__)
        exe_path = f'"{sys.executable}" "{script_path}"'
        
    # Adiciona ao registro do Windows
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    valor = "AtalhosManager"
    try:
        import winreg as reg
        with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE) as hkey:
            reg.SetValueEx(hkey, valor, 0, reg.REG_SZ, exe_path)
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível registrar a inicialização automática:\n{e}")

# --- Código principal ---

if __name__ == "__main__":
    # Tenta registrar na inicialização automática (somente uma vez)
    register_startup()

    # Inicia o listener de atalhos
    listener = AtalhosListener()
    listener.start()

    # Inicia o gerenciador de energia
    manager = PowerManager()
    threading.Thread(target=manager.monitor, daemon=True).start()

    # Cria o ícone da bandeja do sistema
    criar_tray()