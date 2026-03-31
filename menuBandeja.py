import os
import sys
import threading
from PIL import Image
from pystray import Icon, Menu, MenuItem

from config import obter_caminho_recurso

_janela_aberta = False


def _abrir_opcoes(icone, item, gerenciador_clipes_ref, root):
    """Agenda abertura da janela de configurações na thread principal."""
    global _janela_aberta
    if _janela_aberta:
        return
    _janela_aberta = True

    def _on_fechar():
        global _janela_aberta
        _janela_aberta = False

    def _run():
        from interface import abrir_configuracoes
        abrir_configuracoes(
            gerenciador_clipes=gerenciador_clipes_ref[0],
            master=root,
            on_fechar=_on_fechar,
        )

    root.after(0, _run)


def _sair(icone, root):
    icone.stop()
    root.after(0, root.quit)


def criar_icone_system_tray(gerenciador_clipes_ref=None, root=None):
    """Cria o ícone na system tray. Deve rodar em daemon thread."""
    if gerenciador_clipes_ref is None:
        gerenciador_clipes_ref = [None]

    try:
        caminho_icone = obter_caminho_recurso(os.path.join('img', 'icon.ico'))

        if os.path.exists(caminho_icone):
            imagem_icone = Image.open(caminho_icone)
        else:
            imagem_icone = Image.new('RGB', (16, 16), color='blue')

        menu_contexto = Menu(
            MenuItem('Opções',
                     lambda ic, it: _abrir_opcoes(ic, it, gerenciador_clipes_ref, root)),
            MenuItem('Sair', lambda ic, it: _sair(ic, root)),
        )

        Icon('Atalhos', imagem_icone, 'Turbo Atalhos', menu_contexto).run()

    except Exception as e:
        print(f"Erro ao criar ícone da system tray:\n {e}")
        import sys
        sys.exit(1)
        