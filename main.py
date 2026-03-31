import threading
import customtkinter as ctk

from config import carregar_configuracoes
from genAtalhos import GerenciadorAtalhos
from genCopiario import GerenciadorClipes
from genEnergia import GerenciadorEnergia
from menuBandeja import criar_icone_system_tray

# Referência mutável para que menuBandeja passe ao interface
gerenciador_clipes_ref = [None]


def main():
    print("Iniciando Turbo Atalhos!")

    # 1) Energia — monitora processos em segundo plano
    ger_energia = GerenciadorEnergia()
    threading.Thread(target=ger_energia.monitorar_processos, daemon=True).start()

    # 2) Atalhos de teclado (listener pynput)
    ger_atalhos = GerenciadorAtalhos()
    ger_atalhos.iniciar_monitoramento()

    # 3) Janela raiz CTk oculta na thread principal (CustomTkinter exige main thread)
    root = ctk.CTk()
    root.withdraw()

    # 4) Gerenciador de clipes (se habilitado)
    cfg = carregar_configuracoes()
    hist = cfg.get("enable_clip_history", True)
    paste = cfg.get("enable_clip_paste", True)
    if hist or paste:
        msgs = cfg.get("fixed_clip_slots", [""] * 9)
        gerenciador_clipes_ref[0] = GerenciadorClipes(
            enable_history=hist,
            enable_paste=paste,
            mensagens_fixas=msgs,
            root=root,
        )

    # 5) System tray em daemon thread (libera a thread principal para o mainloop)
    threading.Thread(
        target=criar_icone_system_tray,
        args=(gerenciador_clipes_ref, root),
        daemon=True,
    ).start()

    # 6) Mainloop na thread principal
    root.mainloop()


if __name__ == "__main__":
    main()
