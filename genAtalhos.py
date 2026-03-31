import os
import time
import ctypes
import subprocess

from pynput.keyboard import Key, KeyCode, Listener, Controller

from config import (
    carregar_configuracoes, ARQUIVO_CONFIG,
    TEMPO_DUPLO_CLIQUE, FLAG_NOVA_JANELA,
)

controlador_teclado = Controller()

# Mapa seguro de strings → Key do pynput (substitui eval)
KEY_MAP = {
    "Key.alt":          Key.alt,
    "Key.alt_l":        Key.alt_l,
    "Key.alt_r":        Key.alt_r,
    "Key.alt_gr":       Key.alt_gr,
    "Key.backspace":    Key.backspace,
    "Key.caps_lock":    Key.caps_lock,
    "Key.cmd":          Key.cmd,
    "Key.cmd_l":        Key.cmd_l,
    "Key.cmd_r":        Key.cmd_r,
    "Key.ctrl":         Key.ctrl,
    "Key.ctrl_l":       Key.ctrl_l,
    "Key.ctrl_r":       Key.ctrl_r,
    "Key.delete":       Key.delete,
    "Key.down":         Key.down,
    "Key.end":          Key.end,
    "Key.enter":        Key.enter,
    "Key.esc":          Key.esc,
    "Key.f1":           Key.f1,
    "Key.f2":           Key.f2,
    "Key.f3":           Key.f3,
    "Key.f4":           Key.f4,
    "Key.f5":           Key.f5,
    "Key.f6":           Key.f6,
    "Key.f7":           Key.f7,
    "Key.f8":           Key.f8,
    "Key.f9":           Key.f9,
    "Key.f10":          Key.f10,
    "Key.f11":          Key.f11,
    "Key.f12":          Key.f12,
    "Key.home":         Key.home,
    "Key.insert":       Key.insert,
    "Key.left":         Key.left,
    "Key.menu":         Key.menu,
    "Key.num_lock":     Key.num_lock,
    "Key.page_down":    Key.page_down,
    "Key.page_up":      Key.page_up,
    "Key.pause":        Key.pause,
    "Key.print_screen": Key.print_screen,
    "Key.right":        Key.right,
    "Key.scroll_lock":  Key.scroll_lock,
    "Key.shift":        Key.shift,
    "Key.shift_l":      Key.shift_l,
    "Key.shift_r":      Key.shift_r,
    "Key.space":        Key.space,
    "Key.tab":          Key.tab,
    "Key.up":           Key.up,
}


def _resolver_tecla(tecla_str):
    """Converte a string salva no config para o objeto Key/KeyCode correspondente."""
    if tecla_str in KEY_MAP:
        return KEY_MAP[tecla_str]
    # Caractere simples (ex: "a", "5")
    if len(tecla_str) == 1:
        return tecla_str
    return tecla_str


def obter_titulo_janela_ativa():
    """Retorna o título da janela em primeiro plano (Windows)."""
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        tamanho = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(tamanho + 1)
        user32.GetWindowTextW(hwnd, buf, tamanho + 1)
        return buf.value
    except Exception:
        return ""


def executar_comando(comando):
    """Executa um programa ou comando shell."""
    try:
        if os.path.isfile(comando) or comando.lower().endswith('.exe'):
            subprocess.Popen([comando], creationflags=FLAG_NOVA_JANELA)
        else:
            subprocess.Popen(comando, shell=True)
    except Exception:
        pass


class GerenciadorAtalhos:
    def __init__(self):
        cfg = carregar_configuracoes()
        self.atalhos_configurados = cfg["atalhos"]
        self.atalho_calculadora_ativo = cfg.get("enable_calc_percent", True)
        self._ts_config = os.path.getmtime(ARQUIVO_CONFIG)
        self.historico_teclas = {}

    def recarregar_se_necessario(self):
        try:
            ts = os.path.getmtime(ARQUIVO_CONFIG)
            if ts != self._ts_config:
                cfg = carregar_configuracoes()
                self.atalhos_configurados = cfg["atalhos"]
                self.atalho_calculadora_ativo = cfg.get("enable_calc_percent", True)
                self._ts_config = ts
        except OSError:
            pass

    def ao_pressionar_tecla(self, tecla):
        # Atalho especial: % na calculadora via Shift_R
        if (self.atalho_calculadora_ativo
                and tecla == Key.shift_r
                and obter_titulo_janela_ativa() == "Calculadora"):
            controlador_teclado.press(Key.shift)
            controlador_teclado.press('5')
            controlador_teclado.release('5')
            controlador_teclado.release(Key.shift)
            return

        self.recarregar_se_necessario()
        agora = time.time()

        for atalho in self.atalhos_configurados:
            tecla_cfg = _resolver_tecla(atalho['tecla'])

            corresponde = (
                tecla == tecla_cfg
                or (isinstance(tecla, KeyCode)
                    and getattr(tecla, 'char', None) == tecla_cfg)
            )
            if not corresponde:
                continue

            chave = atalho['tecla']
            anterior = self.historico_teclas.get(chave)

            if anterior and (agora - anterior) < TEMPO_DUPLO_CLIQUE:
                executar_comando(atalho['comando'])
                self.historico_teclas[chave] = None
            else:
                self.historico_teclas[chave] = agora

    def iniciar_monitoramento(self):
        Listener(on_press=self.ao_pressionar_tecla).start()
