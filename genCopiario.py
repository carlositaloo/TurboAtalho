import threading
import time

import keyboard
import pyperclip
import customtkinter as ctk

from config import carregar_configuracoes, salvar_configuracoes  # noqa: F401


class GerenciadorClipes:
    """Histórico de clipes e colagem rápida via Ctrl+0..9."""

    def __init__(self, max_clipes=9, enable_history=True, enable_paste=True,
                 mensagens_fixas=None, root=None):
        self.clipes = []
        self.max_clipes = max_clipes
        self.ultima = ""
        self.enable_history = enable_history
        self.enable_paste = enable_paste
        self.mensagens_fixas = (
            mensagens_fixas if mensagens_fixas is not None
            else ["" for _ in range(max_clipes)]
        )
        self._root = root
        self._ignorar_proxima_copia = False
        # Lock protege acesso concorrente a clipes/ultima/flag entre threads
        self._lock = threading.Lock()
        self._configurar_atalhos()
        self._thread = threading.Thread(target=self._monitorar_copiar, daemon=True)
        self._thread.start()

    # -- API pública --

    def atualizar_mensagens_fixas(self, msgs):
        self.mensagens_fixas = msgs

    def atualizar_flags(self, enable_history, enable_paste):
        self.enable_history = enable_history
        self.enable_paste = enable_paste
        self._remover_atalhos()
        self._configurar_atalhos()

    # -- Atalhos --

    def _remover_atalhos(self):
        try:
            keyboard.remove_hotkey("ctrl+0")
        except Exception:
            pass
        for i in range(1, self.max_clipes + 1):
            try:
                keyboard.remove_hotkey(f"ctrl+shift+{i}")
            except Exception:
                pass

    def _configurar_atalhos(self):
        self._remover_atalhos()
        if self.enable_history:
            keyboard.add_hotkey("ctrl+0", self._abrir_historico_em_thread)
        if self.enable_paste:
            for i in range(1, self.max_clipes + 1):
                keyboard.add_hotkey(
                    f"ctrl+shift+{i}", lambda n=i: self._colar_slot(n)
                )

    # -- Monitoramento do clipboard --

    def _monitorar_copiar(self):
        while True:
            time.sleep(0.2)
            try:
                atual = pyperclip.paste()
            except Exception:
                continue
            with self._lock:
                if self._ignorar_proxima_copia:
                    self._ignorar_proxima_copia = False
                    self.ultima = atual
                    continue
                if atual != self.ultima and atual.strip():
                    self.clipes.insert(0, atual)
                    if len(self.clipes) > self.max_clipes:
                        self.clipes.pop()
                    self.ultima = atual

    # -- Colar slot --

    def _colar_slot(self, n):
        if not self.enable_paste:
            return
        idx = n - 1
        texto = ""
        with self._lock:
            if idx < len(self.mensagens_fixas) and self.mensagens_fixas[idx]:
                texto = self.mensagens_fixas[idx]
            elif self.clipes:
                texto = self.clipes[idx] if idx < len(self.clipes) else self.clipes[-1]
            if not texto:
                return
            self._ignorar_proxima_copia = True
        pyperclip.copy(texto)
        keyboard.press_and_release('ctrl+v')

    # -- Popup de histórico --
    # Roda em thread própria com ctk.CTk() para evitar conflito com qualquer
    # outra janela tkinter aberta e o crash do CTkLabel._font no FocusOut.

    def _abrir_historico_em_thread(self):
        """Abre o popup de histórico na thread principal (via root.after) ou em thread dedicada."""
        if self._root is not None:
            self._root.after(0, self._mostrar_historico)
        else:
            threading.Thread(target=self._mostrar_historico, daemon=True).start()

    def _mostrar_historico(self):
        if not self.enable_history:
            return

        with self._lock:
            snapshot = list(self.clipes)

        if self._root is not None:
            janela = ctk.CTkToplevel(self._root)
        else:
            janela = ctk.CTk()
        janela.title("Histórico de Clipes")
        janela.geometry("260x310")
        janela.resizable(False, False)
        janela.attributes('-topmost', True)
        janela.attributes('-toolwindow', True)

        ctk.CTkLabel(janela, text="Histórico de Clipes",
                     font=("Segoe UI", 11, "bold")).pack(pady=(6, 2))

        frame = ctk.CTkScrollableFrame(janela, corner_radius=4)
        frame.pack(fill="both", expand=True, padx=6, pady=(2, 4))

        if not snapshot:
            ctk.CTkLabel(frame, text="(vazio)", font=("Segoe UI", 9)).pack(pady=4)
        else:
            for i, clipe in enumerate(snapshot, 1):
                preview = clipe[:50].replace('\n', ' ')
                if len(clipe) > 50:
                    preview += "…"
                ctk.CTkLabel(
                    frame, text=f"Ctrl+Shift+{i}: {preview}",
                    font=("Segoe UI", 9), anchor="w",
                ).pack(fill="x", padx=2, pady=1)

        ctk.CTkButton(janela, text="Fechar", command=janela.destroy,
                      height=28, font=("Segoe UI", 10),
                      corner_radius=4).pack(pady=(4, 6), padx=6, fill="x")

        def _verificar_foco():
            try:
                if not janela.winfo_exists():
                    return
                w = janela.focus_get()
                # fecha se foco saiu completamente ou foi para fora desta janela
                if w is None or not str(w).startswith(str(janela)):
                    janela.destroy()
            except Exception:
                pass

        def _ativar_foco_out():
            janela.bind('<FocusOut>', lambda _e: janela.after(150, _verificar_foco))

        janela.after(400, _ativar_foco_out)
        janela.after(100, janela.focus_force)
        if self._root is None:
            janela.mainloop()
