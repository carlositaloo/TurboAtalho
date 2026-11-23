"""Turbo Atalho: ícone na bandeja + serviços de teclado, colagens e jogos."""
import os
import sys

from PySide6.QtCore import QLockFile, QObject, QTimer, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from colagens import Slots
from config import CONFIG_DIR, carregar_configuracoes, obter_caminho_recurso
from estilo import aplicar_tema
from janela import JanelaPrincipal
from jogos import MonitorJogos
from popups import Aviso, Quadro, resumo_slot
from sistema import abrir_comando
from teclado import ServicoTeclado, colar_segurando_atalho


class Acoes(QObject):
    """Recebe os sinais da thread do teclado. Por ser QObject da thread principal,
    o Qt entrega os sinais na fila da interface (área de transferência e timers só funcionam aqui)."""

    def __init__(self, slots, aviso):
        super().__init__()
        self.slots, self.aviso = slots, aviso

    @Slot(str)
    def abrir(self, comando):
        abrir_comando(comando)

    @Slot()
    def guardar(self):
        QTimer.singleShot(150, self.guardar_agora)   # espera o app terminar de copiar

    def guardar_agora(self):
        i = self.slots.guardar_da_area()
        if i is None:
            if all(s["fixo"] for s in self.slots.itens):
                self.aviso.mostrar("Todos os slots estão fixados")
            return
        s = self.slots.itens[i]
        if s["tipo"] == "imagem":
            self.aviso.mostrar(f"Guardado no {i + 1}: imagem", self.slots.imagem(i))
        else:
            self.aviso.mostrar(f"Guardado no {i + 1}: {resumo_slot(s)}")

    @Slot(list)
    def avisar_ocupados(self, numeros):
        lista = ", ".join(str(n) for n in numeros)
        self.aviso.mostrar(f"Ctrl+Shift+{lista} já usado por outro programa")

    @Slot(int)
    def colar(self, i):
        if self.slots.copiar_para_area(i):
            QTimer.singleShot(40, colar_segurando_atalho)
        else:
            self.aviso.mostrar(f"Slot {i + 1} está vazio")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Turbo Atalho")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    trava = QLockFile(os.path.join(CONFIG_DIR, "app.lock"))
    if not trava.tryLock(100):
        return 0   # já está aberto

    aplicar_tema(app)
    app.styleHints().colorSchemeChanged.connect(lambda _: aplicar_tema(app))

    cfg = carregar_configuracoes()
    teclado = ServicoTeclado()
    teclado.definir_atalhos(cfg["atalhos"])
    teclado.calc_percent = cfg["calc_percent"]
    slots = Slots(cfg)
    monitor = MonitorJogos()
    monitor.configurar(cfg["jogos"], cfg["plano_fora"])

    aviso = Aviso()
    acoes = Acoes(slots, aviso)
    quadro = Quadro(slots, acoes.guardar_agora)
    janela = JanelaPrincipal(cfg, teclado, slots, monitor, aviso, acoes.guardar_agora)

    teclado.atalho_disparado.connect(acoes.abrir)
    teclado.guardar_copia.connect(acoes.guardar)
    teclado.colar_slot.connect(acoes.colar)
    teclado.abrir_quadro.connect(quadro.abrir)
    teclado.atalhos_ocupados.connect(acoes.avisar_ocupados)

    # ---------- bandeja ----------
    icone = QIcon(obter_caminho_recurso(os.path.join("img", "icon.ico")))
    app.setWindowIcon(icone)
    bandeja = QSystemTrayIcon(icone)
    bandeja.setToolTip("Turbo Atalho")
    menu = QMenu()
    for texto, acao in (
        ("Abrir", lambda: janela.mostrar()),
        ("Colagens", lambda: janela.mostrar(1)),
        ("Jogos", lambda: janela.mostrar(2)),
    ):
        a = QAction(texto, menu)
        a.triggered.connect(acao)
        menu.addAction(a)
    menu.addSeparator()
    sair = QAction("Sair", menu)
    sair.triggered.connect(app.quit)
    menu.addAction(sair)
    bandeja.setContextMenu(menu)
    bandeja.activated.connect(
        lambda motivo: janela.mostrar() if motivo == QSystemTrayIcon.Trigger else None)
    bandeja.show()

    teclado.iniciar()
    monitor.iniciar()
    app.aboutToQuit.connect(teclado.parar)

    if "--abrir" in sys.argv:
        janela.mostrar()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
