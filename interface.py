import os
import ctypes
import customtkinter as ctk
from tkinter import filedialog

from config import (
    carregar_configuracoes, salvar_configuracoes, obter_caminho_recurso,
    OPCOES_PRIORIDADE, OPCOES_PLANOS_ENERGIA,
)

# ---------- Constantes de design ----------
_FONT = "Segoe UI"
_FN_LABEL = (_FONT, 11)
_FN_LABEL_B = (_FONT, 11, "bold")
_FN_INPUT = (_FONT, 10)
_FN_BTN = (_FONT, 10)
_FN_SMALL = (_FONT, 9)
_FN_LIST = (_FONT, 9)
_H_INPUT = 24
_H_BTN = 22
_PAD_X = 4
_PAD_Y = (1, 0)

# Mapa de keysym do tkinter → string "Key.xxx" salva no config (pynput)
_KEYSYM_PARA_PYNPUT = {
    'Num_Lock': 'Key.num_lock', 'Scroll_Lock': 'Key.scroll_lock',
    'Caps_Lock': 'Key.caps_lock',
    'F1': 'Key.f1', 'F2': 'Key.f2', 'F3': 'Key.f3', 'F4': 'Key.f4',
    'F5': 'Key.f5', 'F6': 'Key.f6', 'F7': 'Key.f7', 'F8': 'Key.f8',
    'F9': 'Key.f9', 'F10': 'Key.f10', 'F11': 'Key.f11', 'F12': 'Key.f12',
    'Return': 'Key.enter', 'BackSpace': 'Key.backspace', 'Tab': 'Key.tab',
    'Escape': 'Key.esc', 'space': 'Key.space',
    'Delete': 'Key.delete', 'Insert': 'Key.insert',
    'Home': 'Key.home', 'End': 'Key.end',
    'Prior': 'Key.page_up', 'Next': 'Key.page_down',
    'Up': 'Key.up', 'Down': 'Key.down', 'Left': 'Key.left', 'Right': 'Key.right',
    'Pause': 'Key.pause', 'Print': 'Key.print_screen', 'Menu': 'Key.menu',
    'Control_L': 'Key.ctrl_l', 'Control_R': 'Key.ctrl_r',
    'Shift_L': 'Key.shift_l', 'Shift_R': 'Key.shift_r',
    'Alt_L': 'Key.alt_l', 'Alt_R': 'Key.alt_r',
    'Win_L': 'Key.cmd_l', 'Win_R': 'Key.cmd_r',
    'Super_L': 'Key.cmd_l', 'Super_R': 'Key.cmd_r',
}


class InterfaceOpcoes:
    """Janela de configurações com customtkinter."""

    def __init__(self, gerenciador_clipes=None, master=None, on_fechar=None):
        self.cfg = carregar_configuracoes()
        self._gerenciador_clipes = gerenciador_clipes
        self._on_fechar = on_fechar
        self._indice_atalho_selecionado = None
        self._indice_monitor_selecionado = None

        self._standalone = master is None
        if master is not None:
            self.janela = ctk.CTkToplevel(master)
        else:
            self.janela = ctk.CTk()
        self.janela.title("Turbo Atalhos")
        self.janela.geometry("230x320")
        self.janela.resizable(False, False)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        caminho_icone = obter_caminho_recurso(os.path.join('img', 'icon.ico'))
        if os.path.exists(caminho_icone):
            self.janela.after(300, lambda: self.janela.iconbitmap(caminho_icone))
        self.janela.after(10, self._remover_botao_minimizar)

        # Abas
        self.tabview = ctk.CTkTabview(
            self.janela, corner_radius=4,
            segmented_button_selected_color="#1f6aa5",
            segmented_button_unselected_color="#2b2b2b",
            segmented_button_selected_hover_color="#174f7a",
        )
        self.tabview.pack(padx=1, pady=1, fill="both", expand=True)
        self.tabview._segmented_button.configure(font=(_FONT, 10), height=24)

        self.tab_atalhos = self.tabview.add("Atalhos")
        self.tab_copias = self.tabview.add("Cópias")
        self.tab_energia = self.tabview.add("Energia")

        self._criar_aba_atalhos()
        self._criar_aba_copias()
        self._criar_aba_energia()

    # ========== ABA ATALHOS ==========

    def _criar_aba_atalhos(self):
        tab = self.tab_atalhos

        # Comando
        ctk.CTkLabel(tab, text="Comando:", anchor="w",
                     font=_FN_LABEL_B).pack(pady=_PAD_Y, padx=_PAD_X, fill="x")

        fr_cmd = ctk.CTkFrame(tab, fg_color="transparent")
        fr_cmd.pack(pady=0, padx=_PAD_X, fill="x")

        self.entrada_comando = ctk.CTkEntry(
            fr_cmd, placeholder_text="Diretório do arquivo",
            height=_H_INPUT, font=_FN_INPUT, corner_radius=4,
        )
        self.entrada_comando.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(fr_cmd, text="...", width=24, height=_H_INPUT,
                      font=_FN_BTN, corner_radius=4,
                      command=self._procurar_arquivo).pack(side="right", padx=(2, 0))

        # Tecla
        ctk.CTkLabel(tab, text="Tecla:", anchor="w",
                     font=_FN_LABEL_B).pack(pady=_PAD_Y, padx=_PAD_X, fill="x")

        self.entrada_tecla = ctk.CTkEntry(
            tab, placeholder_text="Clique e pressione a tecla",
            height=_H_INPUT, font=_FN_INPUT, corner_radius=4,
        )
        self.entrada_tecla.pack(pady=0, padx=_PAD_X, fill="x")
        self.entrada_tecla.bind("<KeyPress>", self._capturar_tecla)

        # Botões Remover / Adicionar
        fr_btns = ctk.CTkFrame(tab, fg_color="transparent")
        fr_btns.pack(pady=(2, 0), padx=_PAD_X, fill="x")

        ctk.CTkButton(fr_btns, text="Adicionar", height=_H_BTN,
                      font=_FN_BTN, corner_radius=4,
                      command=self._adicionar_atalho).pack(
            side="left", fill="x", expand=True, padx=(0, 1))
        ctk.CTkButton(fr_btns, text="Remover", height=_H_BTN,
                      font=_FN_BTN, corner_radius=4,
                      command=self._remover_atalho).pack(
            side="right", fill="x", expand=True, padx=(1, 0))

        # Checkbox calculadora
        self.check_calculadora = ctk.CTkCheckBox(
            tab, text="'%' na Calculadora",
            font=_FN_SMALL, checkbox_width=16, checkbox_height=16,
            command=self._alternar_calculadora,
        )
        self.check_calculadora.pack(pady=(2, 0), padx=_PAD_X, anchor="w")
        if self.cfg.get("enable_calc_percent", True):
            self.check_calculadora.select()

        # Lista de atalhos
        self.lista_atalhos = ctk.CTkTextbox(tab, height=55, font=_FN_LIST, corner_radius=4)
        self.lista_atalhos.pack(pady=(2, 0), padx=_PAD_X, fill="both", expand=True)
        self.lista_atalhos.bind("<ButtonRelease-1>", self._selecionar_atalho)
        self.lista_atalhos._textbox.tag_configure("linha_selecionada", background="#1f6aa5", foreground="#ffffff")
        self._atualizar_lista_atalhos()

        # Fechar
        ctk.CTkButton(tab, text="Fechar", command=self.fechar,
                      height=_H_BTN, font=_FN_BTN,
                      corner_radius=4).pack(pady=(2, 2), padx=_PAD_X, fill="x")

    def _atualizar_lista_atalhos(self):
        self.lista_atalhos.configure(state="normal")
        self.lista_atalhos.delete("1.0", "end")
        for at in self.cfg["atalhos"]:
            self.lista_atalhos.insert("end", f"{at['tecla']} → {at['comando']}\n")
        self.lista_atalhos.configure(state="disabled")
        idx = self._indice_atalho_selecionado
        if idx is not None and 0 <= idx < len(self.cfg["atalhos"]):
            tb = self.lista_atalhos._textbox
            tb.tag_add("linha_selecionada", f"{idx + 1}.0", f"{idx + 1}.end+1c")

    def _selecionar_atalho(self, _event=None):
        try:
            idx = int(self.lista_atalhos.index("insert").split(".")[0]) - 1
            if 0 <= idx < len(self.cfg["atalhos"]):
                self._indice_atalho_selecionado = idx
                tb = self.lista_atalhos._textbox
                tb.tag_remove("linha_selecionada", "1.0", "end")
                tb.tag_add("linha_selecionada", f"{idx + 1}.0", f"{idx + 1}.end+1c")
        except Exception:
            pass

    def _adicionar_atalho(self):
        tecla = self.entrada_tecla.get().strip()
        comando = self.entrada_comando.get().strip()
        if not tecla or not comando:
            return
        self.cfg["atalhos"].append({"tecla": tecla, "comando": comando})
        salvar_configuracoes(self.cfg)
        self.entrada_tecla.delete(0, "end")
        self.entrada_comando.delete(0, "end")
        self._atualizar_lista_atalhos()

    def _remover_atalho(self):
        idx = self._indice_atalho_selecionado
        if idx is None or idx >= len(self.cfg["atalhos"]):
            return
        del self.cfg["atalhos"][idx]
        salvar_configuracoes(self.cfg)
        self._indice_atalho_selecionado = None
        self._atualizar_lista_atalhos()

    def _alternar_calculadora(self):
        self.cfg["enable_calc_percent"] = bool(self.check_calculadora.get())
        salvar_configuracoes(self.cfg)

    def _capturar_tecla(self, event):
        """Captura tecla e converte para formato Key.xxx do pynput."""
        if event.keysym in _KEYSYM_PARA_PYNPUT:
            resultado = _KEYSYM_PARA_PYNPUT[event.keysym]
        elif len(event.char) == 1 and event.char.isprintable():
            resultado = event.char.lower()
        elif event.keysym:
            resultado = f"Key.{event.keysym.lower()}"
        else:
            return "break"
        self.entrada_tecla.delete(0, "end")
        self.entrada_tecla.insert(0, resultado)
        return "break"

    def _procurar_arquivo(self):
        arquivo = filedialog.askopenfilename(
            title="Selecionar executável",
            filetypes=[("Executáveis", "*.exe"), ("Todos os arquivos", "*.*")],
        )
        if arquivo:
            self.entrada_comando.delete(0, "end")
            self.entrada_comando.insert(0, os.path.normpath(arquivo))

    # ========== ABA CÓPIAS ==========

    def _criar_aba_copias(self):
        tab = self.tab_copias

        self.check_historico = ctk.CTkCheckBox(
            tab, text="Histórico de clipes (Ctrl+0)",
            font=_FN_SMALL, checkbox_width=16, checkbox_height=16,
            command=self._alternar_historico,
        )
        self.check_historico.pack(pady=(2, 0), padx=_PAD_X, anchor="w")
        if self.cfg.get("enable_clip_history", True):
            self.check_historico.select()

        self.check_colagem = ctk.CTkCheckBox(
            tab, text="Colagem rápida (Ctrl+Shift+1‑9)",
            font=_FN_SMALL, checkbox_width=16, checkbox_height=16,
            command=self._alternar_colagem,
        )
        self.check_colagem.pack(pady=(2, 0), padx=_PAD_X, anchor="w")
        if self.cfg.get("enable_clip_paste", True):
            self.check_colagem.select()

        # Mensagens fixas
        ctk.CTkLabel(tab, text="Mensagens fixas por slot",
                     anchor="w", font=_FN_LABEL_B).pack(pady=(4, 1), padx=_PAD_X, fill="x")

        frame_slots = ctk.CTkFrame(tab, fg_color="transparent")
        frame_slots.pack(pady=0, padx=_PAD_X, fill="both", expand=True)

        # Ctrl+1–8 em 4 linhas × 2 colunas  +  Ctrl+9 na 5a linha
        pares = [(1, 5), (2, 6), (3, 7), (4, 8)]
        for s1, s2 in pares:
            fr = ctk.CTkFrame(frame_slots, fg_color="transparent")
            fr.pack(pady=0, fill="x")
            ctk.CTkLabel(fr, text=f"Ctrl+{s1}:", width=40, anchor="e",
                         font=_FN_SMALL).pack(side="left")
            ctk.CTkButton(fr, text="Editar", width=42, height=20,
                          font=_FN_SMALL, corner_radius=3,
                          command=lambda i=s1-1: self._editar_slot(i)).pack(side="left", padx=2)
            ctk.CTkLabel(fr, text=f"Ctrl+{s2}:", width=40, anchor="e",
                         font=_FN_SMALL).pack(side="left", padx=(4, 0))
            ctk.CTkButton(fr, text="Editar", width=42, height=20,
                          font=_FN_SMALL, corner_radius=3,
                          command=lambda i=s2-1: self._editar_slot(i)).pack(side="left", padx=2)

        fr9 = ctk.CTkFrame(frame_slots, fg_color="transparent")
        fr9.pack(pady=0, fill="x")
        ctk.CTkLabel(fr9, text="Ctrl+9:", width=40, anchor="e",
                     font=_FN_SMALL).pack(side="left")
        ctk.CTkButton(fr9, text="Editar", width=42, height=20,
                      font=_FN_SMALL, corner_radius=3,
                      command=lambda: self._editar_slot(8)).pack(side="left", padx=2)
        ctk.CTkLabel(fr9, text="Histórico:", width=40, anchor="e",
                     font=_FN_SMALL).pack(side="left", padx=(4, 0))
        ctk.CTkButton(fr9, text="Ver", width=42, height=20,
                      font=_FN_SMALL, corner_radius=3,
                      command=self._abrir_historico).pack(side="left", padx=2)

        # Fechar
        ctk.CTkButton(tab, text="Fechar", command=self.fechar,
                      height=_H_BTN, font=_FN_BTN,
                      corner_radius=4).pack(pady=(4, 2), padx=_PAD_X, fill="x")

    def _abrir_historico(self):
        if self._gerenciador_clipes:
            self._gerenciador_clipes._abrir_historico_em_thread()

    def _alternar_historico(self):
        self.cfg["enable_clip_history"] = bool(self.check_historico.get())
        salvar_configuracoes(self.cfg)
        if self._gerenciador_clipes:
            self._gerenciador_clipes.atualizar_flags(
                self.cfg["enable_clip_history"], self.cfg["enable_clip_paste"])

    def _alternar_colagem(self):
        self.cfg["enable_clip_paste"] = bool(self.check_colagem.get())
        salvar_configuracoes(self.cfg)
        if self._gerenciador_clipes:
            self._gerenciador_clipes.atualizar_flags(
                self.cfg["enable_clip_history"], self.cfg["enable_clip_paste"])

    def _editar_slot(self, idx):
        popup = ctk.CTkToplevel(self.janela)
        popup.title(f"Mensagem fixa — Ctrl+Shift+{idx + 1}")
        popup.geometry("360x230")
        popup.resizable(True, True)
        popup.attributes('-topmost', True)

        slots = self.cfg.get("fixed_clip_slots", [""] * 9)
        texto_ini = slots[idx] if idx < len(slots) else ""

        area = ctk.CTkTextbox(popup, font=("Consolas", 11), corner_radius=4)
        area.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        area.insert("1.0", texto_ini)

        def salvar():
            slots = self.cfg.get("fixed_clip_slots", [""] * 9)
            while len(slots) < 9:
                slots.append("")
            slots[idx] = area.get("1.0", "end-1c")
            self.cfg["fixed_clip_slots"] = slots
            salvar_configuracoes(self.cfg)
            if self._gerenciador_clipes:
                self._gerenciador_clipes.atualizar_mensagens_fixas(slots)
            popup.destroy()

        ctk.CTkButton(popup, text="Salvar", command=salvar,
                      height=28, font=_FN_BTN, corner_radius=4).pack(pady=(4, 8), padx=8, fill="x")
        popup.protocol("WM_DELETE_WINDOW", salvar)

    # ========== ABA ENERGIA ==========

    def _criar_aba_energia(self):
        tab = self.tab_energia

        # Processo
        fr_proc = ctk.CTkFrame(tab, fg_color="transparent")
        fr_proc.pack(pady=_PAD_Y, padx=_PAD_X, fill="x")
        ctk.CTkLabel(fr_proc, text="Processo:", width=70, anchor="w",
                     font=_FN_LABEL_B).pack(side="left")
        self.entrada_processo = ctk.CTkEntry(fr_proc, height=_H_INPUT,
                                             font=_FN_INPUT, corner_radius=4)
        self.entrada_processo.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Prioridade (corrigido para alinhar com config)
        fr_prio = ctk.CTkFrame(tab, fg_color="transparent")
        fr_prio.pack(pady=_PAD_Y, padx=_PAD_X, fill="x")
        ctk.CTkLabel(fr_prio, text="Prioridade:", width=70, anchor="w",
                     font=_FN_LABEL_B).pack(side="left")
        self.combo_prioridade = ctk.CTkComboBox(
            fr_prio, values=OPCOES_PRIORIDADE,
            height=_H_INPUT, font=_FN_INPUT,
            dropdown_font=_FN_INPUT, corner_radius=4,
        )
        self.combo_prioridade.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.combo_prioridade.set("Alta")

        # Ao Iniciar
        fr_init = ctk.CTkFrame(tab, fg_color="transparent")
        fr_init.pack(pady=_PAD_Y, padx=_PAD_X, fill="x")
        ctk.CTkLabel(fr_init, text="Ao Iniciar:", width=70, anchor="w",
                     font=_FN_LABEL_B).pack(side="left")
        self.combo_iniciar = ctk.CTkComboBox(
            fr_init, values=OPCOES_PLANOS_ENERGIA,
            height=_H_INPUT, font=_FN_INPUT,
            dropdown_font=_FN_INPUT, corner_radius=4,
        )
        self.combo_iniciar.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.combo_iniciar.set("Alto desempenho")

        # Ao Parar
        fr_stop = ctk.CTkFrame(tab, fg_color="transparent")
        fr_stop.pack(pady=_PAD_Y, padx=_PAD_X, fill="x")
        ctk.CTkLabel(fr_stop, text="Ao Parar:", width=70, anchor="w",
                     font=_FN_LABEL_B).pack(side="left")
        self.combo_parar = ctk.CTkComboBox(
            fr_stop, values=OPCOES_PLANOS_ENERGIA,
            height=_H_INPUT, font=_FN_INPUT,
            dropdown_font=_FN_INPUT, corner_radius=4,
        )
        self.combo_parar.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.combo_parar.set("Equilibrado")

        # Botões
        fr_btns = ctk.CTkFrame(tab, fg_color="transparent")
        fr_btns.pack(pady=(2, 0), padx=_PAD_X, fill="x")

        ctk.CTkButton(fr_btns, text="Adicionar", height=_H_BTN,
                      font=_FN_BTN, corner_radius=4,
                      command=self._adicionar_monitor).pack(
            side="left", fill="x", expand=True, padx=(0, 1))
        ctk.CTkButton(fr_btns, text="Remover", height=_H_BTN,
                      font=_FN_BTN, corner_radius=4,
                      command=self._remover_monitor).pack(
            side="right", fill="x", expand=True, padx=(1, 0))

        # Lista de monitores
        self.lista_energia = ctk.CTkTextbox(tab, height=40, font=_FN_LIST, corner_radius=4)
        self.lista_energia.pack(pady=(2, 0), padx=_PAD_X, fill="both", expand=True)
        self.lista_energia.bind("<ButtonRelease-1>", self._selecionar_monitor)
        self.lista_energia._textbox.tag_configure("linha_selecionada", background="#1f6aa5", foreground="#ffffff")
        self._atualizar_lista_monitores()

        # Fechar
        ctk.CTkButton(tab, text="Fechar", command=self.fechar,
                      height=_H_BTN, font=_FN_BTN,
                      corner_radius=4).pack(pady=(2, 2), padx=_PAD_X, fill="x")

    def _atualizar_lista_monitores(self):
        self.lista_energia.configure(state="normal")
        self.lista_energia.delete("1.0", "end")
        for m in self.cfg["monitores"]:
            self.lista_energia.insert(
                "end",
                f"{m['process']} | {m['priority']} | "
                f"On:{m['power_on'][:5]} | Off:{m['power_off'][:5]}\n",
            )
        self.lista_energia.configure(state="disabled")
        idx = self._indice_monitor_selecionado
        if idx is not None and 0 <= idx < len(self.cfg["monitores"]):
            tb = self.lista_energia._textbox
            tb.tag_add("linha_selecionada", f"{idx + 1}.0", f"{idx + 1}.end+1c")

    def _selecionar_monitor(self, _event=None):
        try:
            idx = int(self.lista_energia.index("insert").split(".")[0]) - 1
            if 0 <= idx < len(self.cfg["monitores"]):
                self._indice_monitor_selecionado = idx
                tb = self.lista_energia._textbox
                tb.tag_remove("linha_selecionada", "1.0", "end")
                tb.tag_add("linha_selecionada", f"{idx + 1}.0", f"{idx + 1}.end+1c")
        except Exception:
            pass

    def _adicionar_monitor(self):
        nome = self.entrada_processo.get().strip()
        if not nome:
            return
        prioridade = self.combo_prioridade.get()
        plano_on = self.combo_iniciar.get()
        plano_off = self.combo_parar.get()
        if plano_on not in OPCOES_PLANOS_ENERGIA or plano_off not in OPCOES_PLANOS_ENERGIA:
            return
        self.cfg["monitores"].append({
            "process": nome,
            "priority": prioridade,
            "power_on": plano_on,
            "power_off": plano_off,
        })
        salvar_configuracoes(self.cfg)
        self.entrada_processo.delete(0, "end")
        self._atualizar_lista_monitores()

    def _remover_monitor(self):
        idx = self._indice_monitor_selecionado
        if idx is None or idx >= len(self.cfg["monitores"]):
            return
        del self.cfg["monitores"][idx]
        salvar_configuracoes(self.cfg)
        self._indice_monitor_selecionado = None
        self._atualizar_lista_monitores()

    # ========== GERAL ==========

    def _remover_botao_minimizar(self):
        GWL_STYLE = -16
        WS_MINIMIZEBOX = 0x00020000
        hwnd = ctypes.windll.user32.GetParent(self.janela.winfo_id())
        if not hwnd:
            hwnd = self.janela.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_MINIMIZEBOX)

    def fechar(self):
        if self._on_fechar:
            self._on_fechar()
        self.janela.destroy()

    def executar(self):
        if self._standalone:
            self.janela.mainloop()


def abrir_configuracoes(gerenciador_clipes=None, master=None, on_fechar=None):
    """Abre a janela de configurações."""
    app = InterfaceOpcoes(gerenciador_clipes=gerenciador_clipes, master=master, on_fechar=on_fechar)
    app.executar()
