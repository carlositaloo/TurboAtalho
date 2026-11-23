"""Vigia os jogos cadastrados: troca o plano de energia quando abrem e volta quando fecham."""
import threading
import time

import psutil
from PySide6.QtCore import QObject, Signal

from config import INTERVALO_MONITOR_JOGOS
from sistema import definir_plano

_CLASSES_PSUTIL = {
    "Acima do normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "Alta": psutil.HIGH_PRIORITY_CLASS,
}


class MonitorJogos(QObject):
    rodando_mudou = Signal(list)   # lista de .exe (minúsculo) abertos

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._jogos = []
        self._plano_fora = ""
        self._abertos = set()
        self._plano_aplicado = None

    def configurar(self, jogos, plano_fora):
        with self._lock:
            self._jogos = [dict(j) for j in jogos]
            self._plano_fora = plano_fora
        self._abertos = set()   # força reavaliar no próximo ciclo

    def iniciar(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                self._ciclo()
            except Exception:
                pass
            time.sleep(INTERVALO_MONITOR_JOGOS)

    def _ciclo(self):
        with self._lock:
            jogos = list(self._jogos)
            plano_fora = self._plano_fora
        alvos = {j["exe"].lower(): j for j in jogos}
        if not alvos:
            if self._abertos:
                self._abertos = set()
                self.rodando_mudou.emit([])
            return

        processos = {}
        for p in psutil.process_iter(["name"]):
            nome = (p.info["name"] or "").lower()
            if nome in alvos:
                processos.setdefault(nome, []).append(p)

        abertos = set(processos)
        if abertos == self._abertos:
            return
        novos = abertos - self._abertos
        self._abertos = abertos
        self.rodando_mudou.emit(sorted(abertos))

        # Garante a prioridade em quem já estava aberto (o registro só vale na próxima abertura)
        for nome in novos:
            classe = _CLASSES_PSUTIL.get(alvos[nome].get("prioridade"))
            if classe is None:
                continue
            for p in processos[nome]:
                try:
                    p.nice(classe)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        # Plano: o do jogo aberto (ordem da lista) ou o "fora do jogo"
        planos_abertos = [alvos[n]["plano"] for n in alvos if n in abertos and alvos[n].get("plano")]
        if planos_abertos:
            desejado = planos_abertos[0]
        elif self._plano_aplicado is not None:
            desejado = plano_fora
        else:
            return   # nenhum jogo abriu ainda: não mexe no plano do usuário
        if desejado and desejado != self._plano_aplicado and definir_plano(desejado):
            self._plano_aplicado = desejado
