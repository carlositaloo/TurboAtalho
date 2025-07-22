# pyinstaller --onefile --noconsole --icon=icon.ico --add-data "icon.png;." main_atalhos.py --clean
# pyinstaller --onefile --noconsole --icon=icon.ico --add-binary "icon.png;." main_atalhos.py --clean

import sys
import os
from subprocess import Popen, run
from pynput.keyboard import Key, Listener
from PIL import Image
from time import time, sleep
from pygetwindow import getActiveWindow
import keyboard as kb
from pystray import Icon, MenuItem, Menu

# Códigos de teclas
tecla_calculadora = Key.num_lock    # Tecla num lock para abrir a calculadora
tecla_notepad = Key.menu            # Tecla menu para abrir o bloco de notas
tecla_terminal = Key.home           # Tecla home para abrir o terminal
tecla_porcentagem = Key.shift_r     # Tecla shift direito para o sinal de porcentagem

# Configurações
limite_pressionamentos = 2
intervalo_pressionamento = 0.5

# Variáveis globais
pressionamentos = 0
ultimo_tempo = 0
app_aberto = False
tecla_pressionada = False

# Função para abrir um aplicativo
def abrir_aplicativo(nome_aplicativo, pressionamentos, app_aberto):
    if pressionamentos >= limite_pressionamentos and not app_aberto:
        if nome_aplicativo == "WindowsTerminal":
            run("wt", shell=True)
        else:
            Popen([nome_aplicativo])
        sleep(2)
        return True
    return False

# Função de callback para quando uma tecla é pressionada
def ao_pressionar(key):
    global pressionamentos, ultimo_tempo, tecla_pressionada, app_aberto
    if not tecla_pressionada:
        tecla_pressionada = True
        tempo_atual = time()

        if tempo_atual - ultimo_tempo <= intervalo_pressionamento:
            pressionamentos += 1
        else:
            pressionamentos = 1

        ultimo_tempo = tempo_atual

        if key == tecla_calculadora:
            app_aberto = abrir_aplicativo("calc.exe", pressionamentos, app_aberto)
        elif key == tecla_notepad:
            app_aberto = abrir_aplicativo("notepad.exe", pressionamentos, app_aberto)
        elif key == tecla_terminal:
            app_aberto = abrir_aplicativo("WindowsTerminal", pressionamentos, app_aberto)

    if key == tecla_porcentagem and getActiveWindow().title == "Calculadora":
        kb.send('shift+5', do_press=True, do_release=True)

# Função de callback para quando uma tecla é solta
def ao_soltar(key):
    global tecla_pressionada, app_aberto
    tecla_pressionada = False
    app_aberto = False

# Função para sair do programa
def sair_do_programa(icon, item):
    icon.stop()
    os._exit(0)  # Força a saída do programa

# Verificar se o script está sendo executado como um executável compilado pelo pyinstaller
if getattr(sys, 'frozen', False):
    exe_path = sys._MEIPASS
else:
    exe_path = os.path.dirname(os.path.abspath(__file__))

# Construir o caminho para o arquivo icon.png dentro dos recursos temporários
icon_path = os.path.join(exe_path, "icon.png")

# Abrir o arquivo icon.png
img_icon = Image.open(icon_path)

# Configuração do ícone na bandeja do sistema
icon = Icon("Copy nota", img_icon, menu=Menu(
    MenuItem("Abrir Terminal", lambda icon, item: abrir_aplicativo("WindowsTerminal", limite_pressionamentos, False)),
    MenuItem("Abrir Notepad", lambda icon, item: abrir_aplicativo("notepad.exe", limite_pressionamentos, False)),
    MenuItem("Abrir Calculadora", lambda icon, item: abrir_aplicativo("calc.exe", limite_pressionamentos, False)),
    MenuItem("Quit", sair_do_programa)
))

# Iniciar o Listener
with Listener(on_press=ao_pressionar, on_release=ao_soltar) as listener:
    icon.run()
    listener.join()
