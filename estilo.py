"""Tema claro/escuro (segue o Windows) e fonte de ícones."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette

CORES = {
    "escuro": {
        "fundo": "#202020", "cartao": "#2b2b2b", "cartao_hover": "#323232", "campo": "#2d2d2d",
        "borda": "#3d3d3d", "texto": "#f3f3f3", "suave": "#a0a0a0", "fraco": "#6e6e6e",
        "acento": "#4cc2ff", "acento_fundo": "#1c3a4d", "acento_texto": "#99dbff",
        "sucesso": "#6ccb5f", "perigo": "#ff99a4",
    },
    "claro": {
        "fundo": "#f3f3f3", "cartao": "#ffffff", "cartao_hover": "#f6f6f6", "campo": "#ffffff",
        "borda": "#dedede", "texto": "#1b1b1b", "suave": "#5f5f5f", "fraco": "#9e9e9e",
        "acento": "#005fb8", "acento_fundo": "#dcebf8", "acento_texto": "#004a8f",
        "sucesso": "#0f7b0f", "perigo": "#c42b1c",
    },
}

# Glifos da fonte Segoe Fluent Icons / Segoe MDL2 Assets
ICONE = {
    "lixo": "", "pino": "", "fixado": "", "pasta": "",
    "fechar": "", "teclado": "", "ok": "", "jogo": "",
    "colar": "", "editar": "",
}


def fonte_icones(tamanho=10):
    familias = QFontDatabase.families()
    nome = "Segoe Fluent Icons" if "Segoe Fluent Icons" in familias else "Segoe MDL2 Assets"
    f = QFont(nome)
    f.setPointSizeF(tamanho)
    return f


def tema_atual():
    escuro = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return CORES["escuro" if escuro else "claro"]


def aplicar_tema(app):
    c = tema_atual()
    pal = QPalette()
    for papel, cor in (
        (QPalette.Window, c["fundo"]), (QPalette.Base, c["campo"]), (QPalette.AlternateBase, c["cartao"]),
        (QPalette.Text, c["texto"]), (QPalette.WindowText, c["texto"]), (QPalette.ButtonText, c["texto"]),
        (QPalette.Button, c["cartao"]), (QPalette.Highlight, c["acento"]), (QPalette.ToolTipBase, c["cartao"]),
        (QPalette.ToolTipText, c["texto"]), (QPalette.PlaceholderText, c["fraco"]),
    ):
        pal.setColor(papel, QColor(cor))
    pal.setColor(QPalette.HighlightedText, QColor(c["fundo"]))
    app.setPalette(pal)
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(QSS.format(**c))


QSS = """
QWidget {{ color: {texto}; font-family: "Segoe UI"; font-size: 9pt; }}
#Janela, #Quadro {{ background: {fundo}; }}
QTabWidget::pane {{ border: none; top: -1px; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {suave}; padding: 5px 0; margin: 6px 2px 2px 2px;
    border-radius: 6px; min-width: 74px; }}
QTabBar::tab:selected {{ background: {acento_fundo}; color: {acento_texto}; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ background: {cartao_hover}; }}
QLabel#Dica {{ color: {suave}; font-size: 8pt; }}
QLabel#Rotulo {{ color: {suave}; font-size: 8pt; margin-top: 2px; }}
QLabel#Secundario {{ color: {suave}; font-size: 8pt; }}
QLabel#Rodando {{ color: {sucesso}; font-size: 8pt; }}
QLabel#Tecla {{ background: {cartao_hover}; border: 1px solid {borda}; border-radius: 4px;
    padding: 0 5px; font-family: "Cascadia Mono", Consolas; font-size: 8pt; }}
QLabel#Num {{ background: {acento_fundo}; color: {acento_texto}; border-radius: 4px; font-weight: 600; }}
QLabel#NumVazio {{ background: {cartao_hover}; color: {fraco}; border-radius: 4px; }}
QLabel#Vazio {{ color: {fraco}; font-style: italic; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ background: {cartao}; border: 1px solid {borda}; border-radius: 6px; margin: 1px 0; }}
QListWidget::item:hover {{ background: {cartao_hover}; }}
QListWidget::item:selected {{ background: {cartao_hover}; border-color: {acento}; }}
QLineEdit, QComboBox {{ background: {campo}; border: 1px solid {borda}; border-radius: 5px;
    padding: 3px 6px; min-height: 16px; selection-background-color: {acento}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {acento}; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox QAbstractItemView {{ background: {cartao}; border: 1px solid {borda}; selection-background-color: {acento_fundo};
    selection-color: {acento_texto}; outline: none; }}
QPushButton {{ background: {cartao}; border: 1px solid {borda}; border-radius: 5px; padding: 4px 8px; }}
QPushButton:hover {{ background: {cartao_hover}; }}
QPushButton:pressed {{ background: {fundo}; }}
QPushButton#Primario {{ background: {acento}; color: {fundo}; border: none; font-weight: 600; }}
QPushButton#Primario:hover {{ background: {acento_texto}; }}
QPushButton#Capturando {{ border-color: {acento}; color: {acento_texto}; }}
QToolButton {{ background: transparent; border: none; border-radius: 4px; color: {suave}; }}
QToolButton:hover {{ background: {cartao_hover}; color: {texto}; }}
QToolButton#Perigo:hover {{ color: {perigo}; }}
QToolButton#Ativo {{ color: {acento}; }}
QCheckBox {{ spacing: 6px; font-size: 8pt; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {borda}; border-radius: 3px; background: {campo}; }}
QCheckBox::indicator:checked {{ background: {acento}; border-color: {acento};
    image: none; }}
QScrollBar:vertical {{ width: 6px; background: transparent; margin: 0; }}
QScrollBar::handle:vertical {{ background: {borda}; border-radius: 3px; min-height: 20px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
#Aviso {{ background: {cartao}; border: 1px solid {borda}; border-radius: 8px; }}
#QuadroCaixa {{ background: {fundo}; border: 1px solid {borda}; border-radius: 8px; }}
QMenu {{ background: {cartao}; border: 1px solid {borda}; padding: 4px; }}
QMenu::item {{ padding: 5px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background: {acento_fundo}; color: {acento_texto}; }}
QToolTip {{ background: {cartao}; color: {texto}; border: 1px solid {borda}; }}
"""
