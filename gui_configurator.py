# gui_configurator.py

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from defaults import DEFAULT_CONFIG

CONFIG_FILE = "config.json"

PRIO_DISPLAY = ["Normal", "Alta"]
PRIO_DISPLAY_TO_INTERNAL = {"Normal": "Normal", "Alta": "High"}
PRIO_INTERNAL_TO_DISPLAY = {v: k for k, v in PRIO_DISPLAY_TO_INTERNAL.items()}

POWER_DISPLAY = [
    "Desempenho máximo",
    "Alto desempenho",
    "Equilibrado",
    "Economia de energia"
]


def load_config(default):
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default.copy()
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


class ConfiguratorUI(tk.Tk):
    PLACEHOLDER_TECLA = "Clique e pressione tecla"

    def __init__(self, default_config):
        super().__init__()

        # Ícone na janela / taskbar (somente .ico)
        ico_ico = os.path.join(os.path.dirname(__file__), 'icons', 'icon2.ico')
        if os.path.exists(ico_ico):
            self.iconbitmap(ico_ico)

        # Dados e configurações
        self.config    = load_config(default_config)
        self.atalhos   = self.config["atalhos"]
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

if __name__ == "__main__":
    app = ConfiguratorUI(DEFAULT_CONFIG)
    app.mainloop()
