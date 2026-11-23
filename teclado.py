"""Teclado global: atalhos de toque duplo, % na Calculadora, Ctrl+C duplo (gancho do `keyboard`,
sem bloquear nada) e Ctrl+Shift+0..9 (RegisterHotKey do Windows, que consome a tecla).

Os callbacks rodam em threads próprias; tudo que mexe com a interface sai por sinais Qt.
"""
import ctypes
import ctypes.wintypes as wt
import threading
import time

import keyboard
from PySide6.QtCore import QObject, Signal

from config import TEMPO_DUPLO_TOQUE, TOTAL_SLOTS
from sistema import titulo_janela_ativa

# Nomes diferentes que o `keyboard` pode dar para a mesma tecla
_APELIDOS = {
    "menu": "menu", "apps": "menu", "applications": "menu",
    "left shift": "shift", "left ctrl": "ctrl", "left alt": "alt",
    "right alt": "alt gr",
}

_MOD_CTRL, _MOD_SHIFT, _MOD_NOREPEAT = 0x2, 0x4, 0x4000
_WM_HOTKEY, _WM_QUIT = 0x0312, 0x0012

_MODIFICADORES = {"shift", "right shift", "ctrl", "right ctrl", "alt", "alt gr",
                  "left windows", "right windows"}


def normalizar(nome):
    nome = (nome or "").lower()
    return _APELIDOS.get(nome, nome)


class ServicoTeclado(QObject):
    atalho_disparado = Signal(str)     # comando a abrir
    guardar_copia = Signal()           # Ctrl+C duas vezes
    colar_slot = Signal(int)           # índice 0..8
    abrir_quadro = Signal()            # Ctrl+Shift+0
    tecla_capturada = Signal(str)      # modo "aperte a tecla" da interface
    atalhos_ocupados = Signal(list)    # números cujo Ctrl+Shift+nº outro app já usa

    def __init__(self):
        super().__init__()
        self._atalhos = {}             # tecla normalizada -> comando
        self.calc_percent = True
        self._ultimo_toque = {}
        self._presas = set()
        self._ultimo_ctrl_c = 0.0
        self._capturando = False
        self._thread_atalhos = None
        self._ignorar_numlock = False
        self._lock = threading.Lock()

    # ---------- configuração ----------

    def definir_atalhos(self, atalhos):
        with self._lock:
            self._atalhos = {normalizar(a["tecla"]): a["comando"] for a in atalhos}

    def capturar_proxima_tecla(self):
        self._capturando = True

    def cancelar_captura(self):
        self._capturando = False

    # ---------- ciclo de vida ----------

    def iniciar(self):
        keyboard.hook(self._ao_evento)
        threading.Thread(target=self._loop_atalhos_windows, daemon=True).start()

    def parar(self):
        keyboard.unhook_all()
        if self._thread_atalhos:
            ctypes.windll.user32.PostThreadMessageW(self._thread_atalhos, _WM_QUIT, 0, 0)

    def _loop_atalhos_windows(self):
        """Ctrl+Shift+0..9 registrados no Windows: o app de destino nunca recebe a tecla."""
        user32 = ctypes.windll.user32
        self._thread_atalhos = ctypes.windll.kernel32.GetCurrentThreadId()
        falharam = []
        for n in range(TOTAL_SLOTS + 1):           # id n ↔ tecla n
            if not user32.RegisterHotKey(None, n + 1, _MOD_CTRL | _MOD_SHIFT | _MOD_NOREPEAT, 0x30 + n):
                falharam.append(n)
        if falharam:
            self.atalhos_ocupados.emit(falharam)
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == _WM_HOTKEY:
                n = msg.wParam - 1
                if n == 0:
                    self.abrir_quadro.emit()
                else:
                    self.colar_slot.emit(n - 1)
        for n in range(TOTAL_SLOTS + 1):
            user32.UnregisterHotKey(None, n + 1)

    # ---------- eventos ----------

    def _ao_evento(self, ev):
        nome = normalizar(ev.name)

        if ev.event_type == keyboard.KEY_UP:
            self._presas.discard(nome)
            return
        if nome in self._presas:      # repetição de tecla segurada
            return
        self._presas.add(nome)

        if self._capturando and nome:
            self._capturando = False
            self.tecla_capturada.emit(nome)
            return

        agora = time.monotonic()

        # % na Calculadora com Shift direito
        if nome == "right shift" and self.calc_percent:
            if titulo_janela_ativa() == "Calculadora":
                keyboard.write("%")
                return

        # Ctrl+C duas vezes → guarda no próximo slot
        if nome == "c" and keyboard.is_pressed("ctrl") and not keyboard.is_pressed("shift") \
                and not keyboard.is_pressed("alt"):
            if agora - self._ultimo_ctrl_c < TEMPO_DUPLO_TOQUE:
                self._ultimo_ctrl_c = 0.0
                self.guardar_copia.emit()
            else:
                self._ultimo_ctrl_c = agora
            return

        # Toque duplo nos atalhos
        with self._lock:
            comando = self._atalhos.get(nome)
        if comando is None:
            return
        if nome not in _MODIFICADORES and any(keyboard.is_pressed(m) for m in ("ctrl", "alt")):
            return
        if nome == "num lock" and self._ignorar_numlock:
            self._ignorar_numlock = False
            return
        anterior = self._ultimo_toque.get(nome, 0.0)
        if agora - anterior < TEMPO_DUPLO_TOQUE:
            self._ultimo_toque[nome] = 0.0
            self.atalho_disparado.emit(comando)
            if nome == "num lock":
                threading.Timer(0.25, self._ligar_numlock).start()
        else:
            self._ultimo_toque[nome] = agora

    def _ligar_numlock(self):
        """O toque duplo liga e desliga o NumLock; deixa ligado no fim (a Calculadora usa o teclado numérico)."""
        if not ctypes.windll.user32.GetKeyState(_VK_NUMLOCK) & 1:
            self._ignorar_numlock = True
            _apertar_vk(_VK_NUMLOCK)


_VK_NUMLOCK = 0x90


def _apertar_vk(vk):
    teclar = ctypes.windll.user32.keybd_event
    teclar(vk, 0x45, 0x1, 0)          # KEYEVENTF_EXTENDEDKEY
    teclar(vk, 0x45, 0x1 | 0x2, 0)    # + KEYEVENTF_KEYUP


def enviar_colar():
    """Cola com Ctrl+V (usado pelo quadro, quando nenhuma tecla está segurada)."""
    keyboard.send("ctrl+v")


def colar_segurando_atalho():
    """Cola enquanto Ctrl+Shift ainda estão segurados (Ctrl+Shift+nº), sem soltá-los de vez:
    assim dá para segurar Ctrl+Shift e apertar vários números seguidos."""
    shift = keyboard.is_pressed("shift")
    ctrl = keyboard.is_pressed("ctrl")
    if shift:
        keyboard.release("shift")          # senão vira Ctrl+Shift+V
    if ctrl:
        keyboard.send("v")                 # Ctrl já está apertado de verdade
    else:
        keyboard.send("ctrl+v")
    if shift and keyboard.is_pressed("shift"):
        keyboard.press("shift")            # devolve o Shift que o usuário ainda segura
        threading.Timer(0.3, _soltar_shift_se_solto).start()


def _soltar_shift_se_solto():
    """Segurança: se o usuário soltou o Shift no meio, não deixa ele 'preso'."""
    if not keyboard.is_pressed("shift"):
        keyboard.release("shift")
