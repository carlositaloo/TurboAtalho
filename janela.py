"""Janela principal (250x360): abas Atalhos, Colagens e Jogos."""
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

import sistema
from config import PRIORIDADES, obter_caminho_recurso, salvar_configuracoes
from estilo import ICONE, fonte_icones
from popups import resumo_slot

LARGURA, ALTURA = 250, 380

_NOMES_CONHECIDOS = {
    "calc.exe": "Calculadora", "notepad.exe": "Bloco de notas", "powershell.exe": "PowerShell",
    "cmd.exe": "Prompt de comando", "explorer.exe": "Explorador", "mspaint.exe": "Paint",
    "wt.exe": "Terminal",
}
_PRIORIDADE_POR_VALOR = {v: k for k, v in PRIORIDADES.items() if v is not None}


def nome_programa(comando):
    base = os.path.basename(comando.strip().strip('"'))
    return _NOMES_CONHECIDOS.get(base.lower(), os.path.splitext(base)[0] or comando)


def nome_tecla(tecla):
    if len(tecla) == 1:
        return tecla.upper()
    return "".join(p.capitalize() for p in tecla.split())


def botao_icone(glifo, dica, perigo=False):
    b = QToolButton()
    b.setText(glifo)
    b.setFont(fonte_icones(9))
    b.setFixedSize(22, 22)
    b.setToolTip(dica)
    b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.NoFocus)
    if perigo:
        b.setObjectName("Perigo")
    return b


def rotulo(texto, nome="Rotulo"):
    r = QLabel(texto)
    r.setObjectName(nome)
    return r


def adicionar_linha(lista, widget, altura):
    item = QListWidgetItem(lista)
    item.setSizeHint(QSize(0, altura))
    lista.setItemWidget(item, widget)
    return item


def nova_lista():
    lista = QListWidget()
    lista.setVerticalScrollMode(QListWidget.ScrollPerPixel)
    lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    lista.setSelectionMode(QListWidget.NoSelection)
    lista.setFocusPolicy(Qt.NoFocus)
    lista.setResizeMode(QListWidget.Adjust)
    return lista


# ===================================================================== Atalhos

class AbaAtalhos(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        self._tecla = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 8)
        lay.setSpacing(5)

        lay.addWidget(rotulo("Toque 2x rápido na tecla para abrir", "Dica"))
        self.lista = nova_lista()
        lay.addWidget(self.lista, 1)

        linha = QHBoxLayout()
        linha.setSpacing(4)
        self.btn_tecla = QPushButton("Tecla")
        self.btn_tecla.setFixedWidth(64)
        self.btn_tecla.setFocusPolicy(Qt.NoFocus)
        self.btn_tecla.setToolTip("Clique e aperte a tecla desejada")
        self.btn_tecla.clicked.connect(self._capturar)
        self.ed_comando = QLineEdit()
        self.ed_comando.setPlaceholderText("calc.exe")
        procurar = botao_icone(ICONE["pasta"], "Procurar programa")
        procurar.clicked.connect(self._procurar)
        linha.addWidget(self.btn_tecla)
        linha.addWidget(self.ed_comando, 1)
        linha.addWidget(procurar)
        lay.addLayout(linha)

        adicionar = QPushButton("Adicionar")
        adicionar.setObjectName("Primario")
        adicionar.clicked.connect(self._adicionar)
        lay.addWidget(adicionar)

        self.ck_calc = QCheckBox("Shift direito vira % na Calculadora")
        self.ck_calc.setChecked(self.j.cfg["calc_percent"])
        self.ck_calc.toggled.connect(self._alternar_calc)
        self.ck_inicio = QCheckBox("Iniciar com o Windows")
        self.ck_inicio.setChecked(sistema.inicia_com_windows())
        self.ck_inicio.toggled.connect(sistema.definir_inicio_com_windows)
        lay.addWidget(self.ck_calc)
        lay.addWidget(self.ck_inicio)

        self.j.teclado.tecla_capturada.connect(self._tecla_capturada)
        self.atualizar()

    def atualizar(self):
        self.lista.clear()
        for i, at in enumerate(self.j.cfg["atalhos"]):
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(6, 0, 2, 0)
            l.setSpacing(6)
            tecla = rotulo(nome_tecla(at["tecla"]), "Tecla")
            nome = QLabel(nome_programa(at["comando"]))
            nome.setToolTip(at["comando"])
            remover = botao_icone(ICONE["lixo"], "Remover", perigo=True)
            remover.clicked.connect(lambda _=False, i=i: self._remover(i))
            l.addWidget(tecla)
            l.addWidget(nome, 1)
            l.addWidget(remover)
            adicionar_linha(self.lista, w, 30)

    def _capturar(self):
        self.btn_tecla.setText("Aperte…")
        self.btn_tecla.setObjectName("Capturando")
        self.btn_tecla.setStyle(self.btn_tecla.style())
        self.j.teclado.capturar_proxima_tecla()

    def _tecla_capturada(self, tecla):
        self._tecla = tecla
        self.btn_tecla.setText(nome_tecla(tecla))
        self.btn_tecla.setObjectName("")
        self.btn_tecla.setStyle(self.btn_tecla.style())

    def _procurar(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Escolher programa", "",
                                                 "Programas (*.exe *.bat *.cmd *.lnk);;Todos (*.*)")
        if arquivo:
            self.ed_comando.setText(os.path.normpath(arquivo))

    def _adicionar(self):
        comando = self.ed_comando.text().strip()
        if not self._tecla or not comando:
            self.j.aviso.mostrar("Escolha a tecla e o programa")
            return
        atalhos = [a for a in self.j.cfg["atalhos"] if a["tecla"] != self._tecla]
        atalhos.append({"tecla": self._tecla, "comando": comando})
        self.j.cfg["atalhos"] = atalhos
        self._salvar()
        self._tecla = ""
        self.btn_tecla.setText("Tecla")
        self.ed_comando.clear()

    def _remover(self, i):
        del self.j.cfg["atalhos"][i]
        self._salvar()

    def _alternar_calc(self, ativo):
        self.j.cfg["calc_percent"] = ativo
        self.j.teclado.calc_percent = ativo
        salvar_configuracoes(self.j.cfg)

    def _salvar(self):
        salvar_configuracoes(self.j.cfg)
        self.j.teclado.definir_atalhos(self.j.cfg["atalhos"])
        self.atualizar()


# ===================================================================== Colagens

class AbaColagens(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 8)
        lay.setSpacing(5)
        lay.addWidget(rotulo("Ctrl+C 2x guarda · Ctrl+Shift+nº cola", "Dica"))
        lay.addWidget(rotulo("Ctrl+Shift+0 abre o quadro de colagens", "Dica"))
        self.lista = nova_lista()
        self.lista.setToolTip("Clique copia · duplo clique edita")
        self.lista.itemClicked.connect(self._clicado)
        self.lista.itemDoubleClicked.connect(self._editar)
        lay.addWidget(self.lista, 1)
        botoes = QHBoxLayout()
        botoes.setSpacing(4)
        guardar = QPushButton("Guardar cópia")
        guardar.setToolTip("Guarda o que está copiado agora (texto ou imagem, ex.: print do Win+Shift+S)")
        guardar.clicked.connect(self.j.ao_guardar)
        limpar = QPushButton("Limpar")
        limpar.setToolTip("Esvazia os slots não fixados")
        limpar.clicked.connect(self.j.slots.limpar_nao_fixados)
        botoes.addWidget(guardar, 1)
        botoes.addWidget(limpar, 1)
        lay.addLayout(botoes)
        self.j.slots.mudou.connect(self.atualizar)
        self.atualizar()

    def atualizar(self):
        self.lista.clear()
        for i, s in enumerate(self.j.slots.itens):
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(5, 0, 2, 0)
            l.setSpacing(6)
            vazio = s["tipo"] == "vazio"
            num = rotulo(str(i + 1), "NumVazio" if vazio else "Num")
            num.setFixedSize(18, 18)
            num.setAlignment(Qt.AlignCenter)
            l.addWidget(num)
            if vazio:
                l.addWidget(rotulo("vazio", "Vazio"), 1)
            elif s["tipo"] == "imagem" and self.j.slots.imagem(i) is not None:
                img = self.j.slots.imagem(i)
                mini = QLabel()
                mini.setPixmap(QPixmap.fromImage(img).scaled(36, 20, Qt.KeepAspectRatio,
                                                             Qt.SmoothTransformation))
                l.addWidget(mini)
                l.addWidget(rotulo(f"{img.width()}×{img.height()}", "Secundario"), 1)
            else:
                texto = QLabel()
                texto.setText(resumo_slot(s, 135, texto.fontMetrics()))
                texto.setToolTip(s["texto"][:500])
                l.addWidget(texto, 1)
            if not vazio:
                pino = botao_icone(ICONE["fixado"] if s["fixo"] else ICONE["pino"],
                                   "Desafixar" if s["fixo"] else "Fixar (não some ao limpar)")
                if s["fixo"]:
                    pino.setObjectName("Ativo")
                pino.clicked.connect(lambda _=False, i=i: self.j.slots.alternar_fixo(i))
                apagar = botao_icone(ICONE["fechar"], "Esvaziar slot", perigo=True)
                apagar.clicked.connect(lambda _=False, i=i: self.j.slots.limpar(i))
                l.addWidget(pino)
                l.addWidget(apagar)
            adicionar_linha(self.lista, w, 28)

    def _clicado(self, item):
        i = self.lista.row(item)
        if self.j.slots.copiar_para_area(i):
            self.j.aviso.mostrar(f"Slot {i + 1} copiado")

    def _editar(self, item):
        i = self.lista.row(item)
        s = self.j.slots.itens[i]
        if s["tipo"] == "imagem":
            return
        texto, ok = QInputDialog.getMultiLineText(self, f"Slot {i + 1}", "Texto:", s["texto"])
        if ok:
            self.j.slots.editar_texto(i, texto)


# ===================================================================== Jogos

class AbaJogos(QWidget):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        self._abertos = set()
        self._planos = sistema.listar_planos()
        self._nome_plano = {g: n for g, n, _ in self._planos}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 8)
        lay.setSpacing(5)
        lay.addWidget(rotulo("Prioridade e plano ao abrir o jogo", "Dica"))
        self.lista = nova_lista()
        lay.addWidget(self.lista, 1)

        linha = QHBoxLayout()
        linha.setSpacing(4)
        self.ed_exe = QLineEdit()
        self.ed_exe.setPlaceholderText("jogo.exe")
        procurar = botao_icone(ICONE["pasta"], "Procurar .exe do jogo")
        procurar.clicked.connect(self._procurar)
        linha.addWidget(self.ed_exe, 1)
        linha.addWidget(procurar)
        lay.addLayout(linha)

        linha2 = QHBoxLayout()
        linha2.setSpacing(4)
        self.cb_prioridade = QComboBox()
        self.cb_prioridade.addItems(list(PRIORIDADES))
        self.cb_prioridade.setCurrentText("Alta")
        self.cb_prioridade.setFixedWidth(82)
        self.cb_prioridade.setToolTip("Prioridade do processo (fica gravada no Windows)")
        self.cb_plano = QComboBox()
        self.cb_plano.addItem("Não mudar plano", "")
        for guid, nome, _ in self._planos:
            self.cb_plano.addItem(nome, guid)
        self._selecionar_plano_mais_forte(self.cb_plano)
        linha2.addWidget(self.cb_prioridade)
        linha2.addWidget(self.cb_plano, 1)
        lay.addLayout(linha2)

        adicionar = QPushButton("Adicionar")
        adicionar.setObjectName("Primario")
        adicionar.clicked.connect(self._adicionar)
        lay.addWidget(adicionar)

        linha3 = QHBoxLayout()
        linha3.setSpacing(4)
        linha3.addWidget(rotulo("Fora do jogo:"))
        self.cb_fora = QComboBox()
        for guid, nome, _ in self._planos:
            self.cb_fora.addItem(nome, guid)
        idx = self.cb_fora.findData(self.j.cfg["plano_fora"])
        if idx >= 0:
            self.cb_fora.setCurrentIndex(idx)
        self.cb_fora.currentIndexChanged.connect(self._mudar_fora)
        linha3.addWidget(self.cb_fora, 1)
        lay.addLayout(linha3)

        self.j.monitor.rodando_mudou.connect(self._rodando)
        self.atualizar()

    def _selecionar_plano_mais_forte(self, combo):
        for preferido in ("Desempenho Máximo", "Ultimate Performance", "Alto desempenho", "High performance"):
            idx = combo.findText(preferido)
            if idx >= 0:
                combo.setCurrentIndex(idx)
                return

    def atualizar(self):
        self.lista.clear()
        for i, jogo in enumerate(self.j.cfg["jogos"]):
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(7, 2, 2, 2)
            l.setSpacing(4)
            col = QVBoxLayout()
            col.setSpacing(0)
            topo = QHBoxLayout()
            topo.setSpacing(6)
            nome = QLabel(f"<b>{jogo['exe']}</b>")
            topo.addWidget(nome)
            if jogo["exe"].lower() in self._abertos:
                topo.addWidget(rotulo("rodando", "Rodando"))
            topo.addStretch(1)
            col.addLayout(topo)
            valor = sistema.ler_prioridade(jogo["exe"])
            prioridade = _PRIORIDADE_POR_VALOR.get(valor, "Normal")
            plano = self._nome_plano.get(jogo.get("plano"), "plano igual")
            col.addWidget(rotulo(f"{prioridade} · {plano}", "Secundario"))
            l.addLayout(col, 1)
            remover = botao_icone(ICONE["lixo"], "Remover", perigo=True)
            remover.clicked.connect(lambda _=False, i=i: self._remover(i))
            l.addWidget(remover)
            adicionar_linha(self.lista, w, 40)

    def _procurar(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Escolher o .exe do jogo", "", "Programas (*.exe)")
        if arquivo:
            self.ed_exe.setText(os.path.basename(arquivo))

    def _adicionar(self):
        exe = os.path.basename(self.ed_exe.text().strip())
        if not exe:
            self.j.aviso.mostrar("Informe o .exe do jogo")
            return
        if not exe.lower().endswith(".exe"):
            exe += ".exe"
        prioridade = self.cb_prioridade.currentText()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok = sistema.gravar_prioridade(exe, PRIORIDADES[prioridade])
        finally:
            QApplication.restoreOverrideCursor()
        if not ok:
            self.j.aviso.mostrar("Prioridade não aplicada (permissão negada)")
        jogos = [j for j in self.j.cfg["jogos"] if j["exe"].lower() != exe.lower()]
        jogos.append({"exe": exe, "prioridade": prioridade, "plano": self.cb_plano.currentData()})
        self.j.cfg["jogos"] = jogos
        self.ed_exe.clear()
        self._salvar()

    def _remover(self, i):
        exe = self.j.cfg["jogos"][i]["exe"]
        if not sistema.gravar_prioridade(exe, None):
            self.j.aviso.mostrar("Não removido: permissão negada")
            return
        del self.j.cfg["jogos"][i]
        self._salvar()

    def _mudar_fora(self):
        self.j.cfg["plano_fora"] = self.cb_fora.currentData()
        self._salvar()

    def _rodando(self, abertos):
        self._abertos = set(abertos)
        self.atualizar()

    def _salvar(self):
        salvar_configuracoes(self.j.cfg)
        self.j.monitor.configurar(self.j.cfg["jogos"], self.j.cfg["plano_fora"])
        self.atualizar()


# ===================================================================== Janela

class JanelaPrincipal(QWidget):
    def __init__(self, cfg, teclado, slots, monitor, aviso, ao_guardar):
        super().__init__()
        self.cfg, self.teclado, self.slots, self.monitor, self.aviso = cfg, teclado, slots, monitor, aviso
        self.ao_guardar = ao_guardar
        self.setObjectName("Janela")
        self.setWindowTitle("Turbo Atalho")
        self.setWindowIcon(QIcon(obter_caminho_recurso(os.path.join("img", "icon.ico"))))
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.MSWindowsFixedSizeDialogHint)
        self.setFixedSize(LARGURA, ALTURA)

        abas = QTabWidget()
        abas.setDocumentMode(True)
        abas.tabBar().setExpanding(True)
        abas.addTab(AbaAtalhos(self), "Atalhos")
        abas.addTab(AbaColagens(self), "Colagens")
        abas.addTab(AbaJogos(self), "Jogos")
        self.abas = abas

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(abas)

    def mostrar(self, aba=None):
        if aba is not None:
            self.abas.setCurrentIndex(aba)
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, ev):
        self.teclado.cancelar_captura()
        ev.ignore()
        self.hide()
