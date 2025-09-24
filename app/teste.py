import keyboard
import pyperclip
import time
import threading

# Armazena no máximo 9 clipes
clipes = []


def monitorar_copiar():
    """Monitora Ctrl+C e salva no histórico."""
    global clipes
    ultima = ""
    while True:
        time.sleep(0.1)
        if keyboard.is_pressed("ctrl+c"):
            time.sleep(0.2)  # evita múltiplas capturas
            atual = pyperclip.paste()
            if atual != ultima and atual.strip():
                clipes.insert(0, atual)  # coloca na frente
                if len(clipes) > 9:
                    clipes.pop()  # remove o mais antigo
                print(f"[+] Copiado: {atual[:40]}...")
                ultima = atual


def mostrar_historico():
    """Mostra o histórico de todos os clipes salvos."""
    print("\n=== Histórico de Clipes ===")
    for i, clipe in enumerate(clipes, 1):
        print(f"Ctrl+{i}: {clipe[:40]}{'...' if len(clipe) > 40 else ''}")
    print("========================")


def configurar_slots():
    """Define atalhos Ctrl+0 até Ctrl+9 para colar e mostrar histórico."""
    keyboard.add_hotkey(
        "ctrl+0", mostrar_historico)  # adiciona atalho para histórico
    for i in range(1, 10):  # só até 9
        keyboard.add_hotkey(f"ctrl+{i}", lambda i=i: colar_slot(i))


def colar_slot(n):
    """Cola o conteúdo do slot escolhido."""
    if len(clipes) >= n:
        pyperclip.copy(clipes[n-1])
        print(f"[>] Slot {n} colado: {clipes[n-1][:40]}...")
        # simula Ctrl+V
        keyboard.write(clipes[n-1])
    else:
        print(f"[x] Slot {n} vazio.")


if __name__ == "__main__":
    print("Gerenciador de múltiplos Ctrl+C iniciado!")
    print("Use Ctrl+1 até Ctrl+9 para colar dos slots.")
    print("Use Ctrl+0 para ver o histórico de clipes.")

    configurar_slots()
    t = threading.Thread(target=monitorar_copiar, daemon=True)
    t.start()

    keyboard.wait()  # mantém rodando
