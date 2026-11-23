"""Janelinhas flutuantes: aviso rápido no canto e quadro de colagens (Ctrl+Shift+0)."""
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from sistema import focar_janela, janela_ativa
from teclado import enviar_colar


def resumo_slot(slot, largura_max=None, fm=None):
    texto = " ".join(slot["texto"].split())
    if fm is not None and largura_max:
        texto = fm.elidedText(texto, Qt.ElideRight, largura_max)
    return texto


class Aviso(QWidget):
    """Balãozinho no canto inferior direito que some sozinho, sem roubar o foco."""

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        caixa = QFrame(self)
        caixa.setObjectName("Aviso")
        externo = QVBoxLayout(self)
        externo.setContentsMargins(0, 0, 0, 0)
        externo.addWidget(caixa)
        lay = QHBoxLayout(caixa)
        lay.setContentsMargins(10, 8, 12, 8)
        lay.setSpacing(8)
        self._imagem = QLabel()
        self._texto = QLabel()
        self._texto.setMaximumWidth(240)
        lay.addWidget(self._imagem)
        lay.addWidget(self._texto, 1)
        self._timer = QTimer(self, singleShot=True, timeout=self.hide)

    def mostrar(self, texto, imagem=None):
        fm = self._texto.fontMetrics()
        self._texto.setText(fm.elidedText(texto, Qt.ElideRight, 240))
        if imagem is not None and not imagem.isNull():
            self._imagem.setPixmap(QPixmap.fromImage(imagem).scaled(
                36, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._imagem.show()
        else:
            self._imagem.hide()
        self.adjustSize()
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 12, area.bottom() - self.height() - 12)
        self.show()
        self.raise_()
        self._timer.start(1800)


class Quadro(QWidget):
    """Lista os slots perto do mouse; aperte o número (ou clique) para colar na janela anterior."""

    def __init__(self, slots, ao_guardar):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("Quadro")
        self._slots = slots
        self._ao_guardar = ao_guardar
        self._anterior = None
        caixa = QFrame(self)
        caixa.setObjectName("QuadroCaixa")
        externo = QVBoxLayout(self)
        externo.setContentsMargins(0, 0, 0, 0)
        externo.addWidget(caixa)
        self._lay = QVBoxLayout(caixa)
        self._lay.setContentsMargins(8, 8, 8, 8)
        self._lay.setSpacing(3)
        self.setFixedWidth(230)

    def _montar(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        titulo = QLabel("Colagens  ·  aperte o número  ·  Esc fecha")
        titulo.setObjectName("Dica")
        self._lay.addWidget(titulo)
        vazio = True
        for i, s in enumerate(self._slots.itens):
            if s["tipo"] == "vazio":
                continue
            vazio = False
            linha = _LinhaQuadro(i, s, self._slots.imagem(i), self._escolher)
            self._lay.addWidget(linha)
        if vazio:
            nada = QLabel("Nenhum slot guardado.\nCopie com Ctrl+C duas vezes.")
            nada.setObjectName("Vazio")
            self._lay.addWidget(nada)

        rodape = QWidget()
        lr = QHBoxLayout(rodape)
        lr.setContentsMargins(0, 4, 0, 0)
        lr.setSpacing(4)
        for texto, dica, acao in (
            ("Guardar cópia  G", "Guarda o que está copiado agora (texto ou imagem, ex.: print do Win+Shift+S)",
             self._guardar),
            ("Limpar  Del", "Esvazia os slots não fixados", self._limpar),
        ):
            b = QPushButton(texto)
            b.setToolTip(dica)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(acao)
            lr.addWidget(b, 1)
        self._lay.addWidget(rodape)

    def _remontar(self):
        topo = self.pos()
        self._montar()
        self.adjustSize()
        self.move(topo)

    def _guardar(self):
        self._ao_guardar()
        self._remontar()

    def _limpar(self):
        self._slots.limpar_nao_fixados()
        self._remontar()

    def abrir(self):
        self._anterior = janela_ativa()
        self._montar()
        self.adjustSize()
        pos = QCursor.pos() + QPoint(8, 8)
        area = QGuiApplication.screenAt(QCursor.pos()).availableGeometry()
        pos.setX(min(pos.x(), area.right() - self.width()))
        pos.setY(min(pos.y(), area.bottom() - self.height()))
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()
        focar_janela(int(self.winId()))

    def _escolher(self, i):
        self.hide()
        if not self._slots.copiar_para_area(i):
            return
        focar_janela(self._anterior)
        QTimer.singleShot(90, enviar_colar)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.hide()
        elif Qt.Key_1 <= ev.key() <= Qt.Key_9:
            self._escolher(ev.key() - Qt.Key_1)
        elif ev.key() == Qt.Key_G:
            self._guardar()
        elif ev.key() == Qt.Key_Delete:
            self._limpar()
        else:
            super().keyPressEvent(ev)

    def changeEvent(self, ev):
        if ev.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide()
        super().changeEvent(ev)


class _LinhaQuadro(QFrame):
    def __init__(self, i, slot, imagem, ao_clicar):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self._i, self._ao_clicar = i, ao_clicar
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)
        num = QLabel(str(i + 1))
        num.setObjectName("Num")
        num.setFixedSize(18, 18)
        num.setAlignment(Qt.AlignCenter)
        lay.addWidget(num)
        if slot["tipo"] == "imagem" and imagem is not None:
            miniatura = QLabel()
            miniatura.setPixmap(QPixmap.fromImage(imagem).scaled(40, 22, Qt.KeepAspectRatio,
                                                                 Qt.SmoothTransformation))
            lay.addWidget(miniatura)
            lay.addWidget(QLabel(f"Imagem {imagem.width()}×{imagem.height()}"), 1)
        else:
            texto = QLabel()
            texto.setText(resumo_slot(slot, 170, texto.fontMetrics()))
            lay.addWidget(texto, 1)

    def mouseReleaseEvent(self, ev):
        self._ao_clicar(self._i)
