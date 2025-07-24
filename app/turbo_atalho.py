# app.py

import json
import os
import sys
import threading
import time
import subprocess
import psutil
import re
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from pynput.keyboard import Key, KeyCode, Listener, Controller
from pystray import Icon, MenuItem, Menu
from PIL import Image

DEFAULT_CONFIG = {
    "enable_calc_percent": True,
    
    "atalhos": [
        {"tecla": "Key.num_lock", "comando": "calc.exe"},
        {"tecla": "Key.menu",     "comando": "notepad.exe"},
        {"tecla": "Key.home",     "comando": "powershell.exe"},
    ],
    "monitores": [
    ],
}

APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
CONFIG_DIR = os.path.join(APPDATA, 'TurboAtalho')
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, 'config.json')

os.makedirs(CONFIG_DIR, exist_ok=True)

INTERVALO_MONITORAMENTO = 1
TEMPO_DUPLO_CLIQUE = 0.5

DIRETORIO_ATUAL = os.path.dirname(__file__)

if getattr(sys, 'frozen', False):
    DIRETORIO_BASE = sys._MEIPASS
else:
    DIRETORIO_BASE = os.path.dirname(__file__)

DIRETORIO_ICONES = os.path.join(DIRETORIO_BASE, 'icons')

controlador_teclado = Controller()

MAPA_PRIORIDADES = {
    "Normal": psutil.NORMAL_PRIORITY_CLASS,
    "High":   psutil.HIGH_PRIORITY_CLASS
}

PLANOS_ENERGIA_PADRAO = {
    "Alto desempenho":      "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c".lower(),
    "Equilibrado":          "381b4222-f694-41f0-9685-ff5bb260df2e".lower(),
    "Economia de energia":  "a1841308-3541-4fab-bc81-f71556f20b4a".lower()
}

FLAG_NOVA_JANELA = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0

OPCOES_PRIORIDADE_EXIBICAO = ["Normal", "Alta"]

PRIORIDADE_EXIBICAO_PARA_INTERNO = {"Normal": "Normal", "Alta": "High"}
PRIORIDADE_INTERNO_PARA_EXIBICAO = {
    valor: chave for chave, valor in PRIORIDADE_EXIBICAO_PARA_INTERNO.items()}

OPCOES_PLANOS_ENERGIA = [
    "Alto desempenho",
    "Equilibrado",
    "Economia de energia"
]

def obter_guids_planos_energia():
    try:
        resultado = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        return {}
    
    mapeamento_planos = {}
    for linha in resultado.stdout.splitlines():
        match = re.search(r"GUID:\s*([0-9A-Fa-f-]+)\s*\((.+?)\)", linha)
        if match:
            guid = match.group(1).lower()
            nome = match.group(2).strip()
            mapeamento_planos[nome] = guid
    
    return mapeamento_planos

def obter_titulo_janela_ativa():
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        tamanho = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(tamanho + 1)
        user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
        return buffer.value
    except Exception:
        return ""

def carregar_configuracoes(configuracao_padrao=DEFAULT_CONFIG):
    if not os.path.exists(ARQUIVO_CONFIG):
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as arquivo:
            json.dump(configuracao_padrao, arquivo,
                      indent=4, ensure_ascii=False)
        return configuracao_padrao.copy()

    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, FileNotFoundError):
        return configuracao_padrao.copy()

def salvar_configuracoes(configuracoes):
    try:
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as arquivo:
            json.dump(configuracoes, arquivo, indent=4, ensure_ascii=False)
    except Exception:
        messagebox.showerror(
            "Erro", "Não foi possível salvar as configurações")

def executar_comando(comando):
    try:
        if os.path.isfile(comando) or comando.lower().endswith('.exe'):
            subprocess.Popen([comando], creationflags=FLAG_NOVA_JANELA)
        else:
            subprocess.Popen(comando, shell=True)
    except Exception as erro:
        pass

class GerenciadorAtalhos:
    def __init__(self):
        configuracoes = carregar_configuracoes()
        
        self.atalhos_configurados = configuracoes["atalhos"]
        self.atalho_calculadora_ativo = configuracoes.get("enable_calc_percent", True)
        
        self.timestamp_config = os.path.getmtime(ARQUIVO_CONFIG)
        
        self.historico_teclas = {}

    def recarregar_se_necessario(self):
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                configuracoes = carregar_configuracoes()
                self.atalhos_configurados = configuracoes["atalhos"]
                self.atalho_calculadora_ativo = configuracoes.get("enable_calc_percent", True)
                self.timestamp_config = timestamp_atual
        except OSError:
            pass

    def ao_pressionar_tecla(self, tecla):
        if (self.atalho_calculadora_ativo and 
            tecla == Key.shift_r and 
            obter_titulo_janela_ativa() == "Calculadora"):
            
            controlador_teclado.press(Key.shift)
            controlador_teclado.press('5')
            controlador_teclado.release('5')
            controlador_teclado.release(Key.shift)
            return

        self.recarregar_se_necessario()
        tempo_atual = time.time()
        
        for atalho in self.atalhos_configurados:
            try:
                tecla_configurada = eval(atalho['tecla'])
            except (NameError, SyntaxError):
                tecla_configurada = atalho['tecla']
            
            tecla_corresponde = (
                tecla == tecla_configurada or
                (isinstance(tecla, KeyCode) and 
                 getattr(tecla, 'char', None) == tecla_configurada)
            )
            
            if not tecla_corresponde:
                continue
            
            chave_atalho = atalho['tecla']
            tempo_anterior = self.historico_teclas.get(chave_atalho)
            
            if tempo_anterior and (tempo_atual - tempo_anterior) < TEMPO_DUPLO_CLIQUE:
                executar_comando(atalho['comando'])
                self.historico_teclas[chave_atalho] = None
            else:
                self.historico_teclas[chave_atalho] = tempo_atual

    def iniciar_monitoramento(self):
        Listener(on_press=self.ao_pressionar_tecla).start()

class GerenciadorEnergia:
    def __init__(self):
        configuracoes = carregar_configuracoes()
        
        self.processos_monitorados = configuracoes["monitores"]
        self.timestamp_config = os.path.getmtime(ARQUIVO_CONFIG)
        
        self.mapa_planos_sistema = obter_guids_planos_energia()
        
        self.estado_processos = {
            processo['process'].lower(): False 
            for processo in self.processos_monitorados
        }

    def recarregar_se_necessario(self):
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                configuracoes = carregar_configuracoes()
                self.processos_monitorados = configuracoes["monitores"]
                self.timestamp_config = timestamp_atual
                self.mapa_planos_sistema = obter_guids_planos_energia()
                
                self.estado_processos = {
                    processo['process'].lower(): False 
                    for processo in self.processos_monitorados
                }
        except OSError:
            pass

    def monitorar_processos(self):
        while True:
            try:
                self.recarregar_se_necessario()
                
                for config_processo in self.processos_monitorados:
                    nome_processo = config_processo['process'].lower()
                    
                    processos_encontrados = [
                        processo for processo in psutil.process_iter(['name'])
                        if (processo.info['name'] and 
                            processo.info['name'].lower().startswith(nome_processo))
                    ]
                    
                    processo_ativo = bool(processos_encontrados)
                    
                    guid_plano_ativo = (
                        self.mapa_planos_sistema.get(config_processo['power_on']) or
                        PLANOS_ENERGIA_PADRAO.get(config_processo['power_on']) or
                        PLANOS_ENERGIA_PADRAO["Alto desempenho"]
                    )
                    
                    guid_plano_inativo = (
                        self.mapa_planos_sistema.get(config_processo['power_off']) or
                        PLANOS_ENERGIA_PADRAO.get(config_processo['power_off']) or
                        PLANOS_ENERGIA_PADRAO["Equilibrado"]
                    )
                    
                    if processo_ativo and not self.estado_processos[nome_processo]:
                        try:
                            subprocess.run(
                                ["powercfg", "-setactive", guid_plano_ativo], 
                                check=True
                            )
                        except subprocess.CalledProcessError:
                            pass
                        
                        for processo in processos_encontrados:
                            try:
                                prioridade = MAPA_PRIORIDADES.get(
                                    config_processo['priority'], 
                                    psutil.NORMAL_PRIORITY_CLASS
                                )
                                processo.nice(prioridade)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                        
                        self.estado_processos[nome_processo] = True
                    
                    elif not processo_ativo and self.estado_processos[nome_processo]:
                        try:
                            subprocess.run(
                                ["powercfg", "-setactive", guid_plano_inativo], 
                                check=True
                            )
                        except subprocess.CalledProcessError:
                            pass
                        
                        self.estado_processos[nome_processo] = False
                
            except Exception:
                pass
            
            time.sleep(INTERVALO_MONITORAMENTO)

class InterfaceConfigurador(tk.Tk):
    PLACEHOLDER_TECLA = "Clique e pressione tecla"

    def __init__(self, configuracao_padrao):
        super().__init__()

        self._configurar_janela()

        self._inicializar_dados(configuracao_padrao)

        self._construir_interface()

    def _configurar_janela(self):
        caminho_icone = os.path.join(
            os.path.dirname(__file__), 'icons', 'icon.ico')
        if os.path.exists(caminho_icone):
            try:
                self.iconbitmap(caminho_icone)
            except tk.TclError:
                pass

        self.title("Configurar Atalhos & Energia")
        self.geometry("280x300")
        self.resizable(False, False)

    def _inicializar_dados(self, configuracao_padrao):
        self.configuracoes = carregar_configuracoes(configuracao_padrao)

        self.lista_atalhos = self.configuracoes["atalhos"]
        self.lista_monitores = self.configuracoes["monitores"]

        self.atalho_calculadora_ativo = tk.BooleanVar(
            value=self.configuracoes.get("enable_calc_percent", True)
        )

    def _construir_interface(self):
        notebook = ttk.Notebook(self)
        notebook.place(x=0, y=0, width=280, height=380)

        self._construir_aba_atalhos(notebook)
        self._construir_aba_energia(notebook)

        ttk.Button(self, text="Fechar", command=self.destroy)\
            .place(x=200, y=395, width=70, height=28)

    def _construir_aba_atalhos(self, notebook):
        aba = ttk.Frame(notebook)
        notebook.add(aba, text="Gerenciar Atalhos")
        aba.columnconfigure(1, weight=1)

        ttk.Label(aba, text="Tecla:")\
            .grid(row=0, column=0, sticky='w', padx=3, pady=2)

        self.campo_tecla = ttk.Entry(aba, width=20)
        self.campo_tecla.grid(row=0, column=1, columnspan=2,
                              sticky='ew', padx=3, pady=2)
        self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.campo_tecla.bind("<FocusIn>", self._ao_focar_campo_tecla)
        self.campo_tecla.bind("<FocusOut>", self._ao_desfocar_campo_tecla)

        ttk.Label(aba, text="Comando:")\
            .grid(row=1, column=0, sticky='w', padx=3, pady=2)

        self.campo_comando = ttk.Entry(aba, width=20)
        self.campo_comando.grid(row=1, column=1, sticky='ew', padx=3, pady=2)

        ttk.Button(aba, text="…", width=2, command=self._procurar_arquivo)\
            .grid(row=1, column=2, padx=3, pady=2)

        ttk.Button(aba, text="Adicionar", command=self._adicionar_atalho)\
            .grid(row=2, column=0, padx=3, pady=4, sticky='w')
        ttk.Button(aba, text="Remover Selecionado", command=self._remover_atalho)\
            .grid(row=2, column=1, columnspan=2, padx=3, pady=4, sticky='e')

        checkbox_calculadora = ttk.Checkbutton(
            aba,
            text="Ativar '%' na Calculadora (Shift‑Direito)",
            variable=self.atalho_calculadora_ativo,
            command=self._alternar_atalho_calculadora
        )
        checkbox_calculadora.grid(
            row=3, column=0, columnspan=3, sticky='w', padx=3, pady=4)

        self.lista_widget_atalhos = tk.Listbox(aba, height=8)
        self.lista_widget_atalhos.grid(
            row=4, column=0, columnspan=3, sticky='nsew', padx=3, pady=2)
        aba.rowconfigure(4, weight=1)

        self._atualizar_lista_atalhos()

    def _construir_aba_energia(self, notebook):
        aba = ttk.Frame(notebook)
        notebook.add(aba, text="Gerenciar Energia")
        aba.columnconfigure(1, weight=1)

        ttk.Label(aba, text="Processo:")\
            .grid(row=0, column=0, sticky='w', padx=3, pady=2)

        self.campo_processo = ttk.Entry(aba, width=16)
        self.campo_processo.grid(row=0, column=1, sticky='ew', padx=3, pady=2)

        ttk.Label(aba, text="Prioridade:")\
            .grid(row=1, column=0, sticky='w', padx=3, pady=2)

        self.combo_prioridade = ttk.Combobox(
            aba,
            values=OPCOES_PRIORIDADE_EXIBICAO,
            width=14,
            state='readonly'
        )
        self.combo_prioridade.grid(
            row=1, column=1, sticky='ew', padx=3, pady=2)
        self.combo_prioridade.set(
            OPCOES_PRIORIDADE_EXIBICAO[1])

        ttk.Label(aba, text="Plano ao Iniciar:")\
            .grid(row=2, column=0, sticky='w', padx=3, pady=2)

        self.combo_plano_iniciar = ttk.Combobox(
            aba,
            values=OPCOES_PLANOS_ENERGIA,
            width=14,
            state='readonly'
        )
        self.combo_plano_iniciar.grid(
            row=2, column=1, sticky='ew', padx=3, pady=2)
        self.combo_plano_iniciar.set(
            OPCOES_PLANOS_ENERGIA[0])

        ttk.Label(aba, text="Plano ao Parar:")\
            .grid(row=3, column=0, sticky='w', padx=3, pady=2)

        self.combo_plano_parar = ttk.Combobox(
            aba,
            values=OPCOES_PLANOS_ENERGIA,
            width=14,
            state='readonly'
        )
        self.combo_plano_parar.grid(
            row=3, column=1, sticky='ew', padx=3, pady=2)
        self.combo_plano_parar.set(OPCOES_PLANOS_ENERGIA[1])

        ttk.Button(aba, text="Adicionar", command=self._adicionar_monitor)\
            .grid(row=4, column=0, padx=3, pady=4, sticky='w')
        ttk.Button(aba, text="Remover Selecionado", command=self._remover_monitor)\
            .grid(row=4, column=1, padx=3, pady=4, sticky='e')

        self.lista_widget_monitores = tk.Listbox(aba, height=8)
        self.lista_widget_monitores.grid(
            row=5, column=0, columnspan=3, sticky='nsew', padx=3, pady=2)
        aba.rowconfigure(5, weight=1)

        self._atualizar_lista_monitores()

    def _ao_focar_campo_tecla(self, evento):
        if self.campo_tecla.get() == self.PLACEHOLDER_TECLA:
            self.campo_tecla.delete(0, tk.END)
            self.bind_all("<KeyPress>", self._capturar_tecla_pressionada)

    def _ao_desfocar_campo_tecla(self, evento):
        if not self.campo_tecla.get():
            self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)

    def _capturar_tecla_pressionada(self, evento):
        if evento.char and len(evento.char) == 1:
            representacao_tecla = evento.char
        else:
            representacao_tecla = f"Key.{evento.keysym.lower()}"

        self.campo_tecla.delete(0, tk.END)
        self.campo_tecla.insert(0, representacao_tecla)

        self.unbind_all("<KeyPress>")

    def _atualizar_lista_atalhos(self):
        self.lista_widget_atalhos.delete(0, tk.END)
        for atalho in self.lista_atalhos:
            texto_atalho = f"{atalho['tecla']} → {atalho['comando']}"
            self.lista_widget_atalhos.insert(tk.END, texto_atalho)

    def _adicionar_atalho(self):
        tecla = self.campo_tecla.get().strip()
        comando = self.campo_comando.get().strip()

        if not tecla or tecla.startswith("Clique") or not comando:
            messagebox.showwarning("Atenção", "Defina tecla e comando válidos")
            return

        novo_atalho = {"tecla": tecla, "comando": comando}
        self.lista_atalhos.append(novo_atalho)

        self.configuracoes["atalhos"] = self.lista_atalhos
        salvar_configuracoes(self.configuracoes)

        self.campo_tecla.delete(0, tk.END)
        self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.campo_comando.delete(0, tk.END)

        self._atualizar_lista_atalhos()

    def _remover_atalho(self):
        selecao = self.lista_widget_atalhos.curselection()
        if not selecao:
            messagebox.showinfo(
                "Informação", "Selecione um atalho para remover")
            return

        indice = selecao[0]
        del self.lista_atalhos[indice]

        self.configuracoes["atalhos"] = self.lista_atalhos
        salvar_configuracoes(self.configuracoes)

        self._atualizar_lista_atalhos()

    def _alternar_atalho_calculadora(self):
        self.configuracoes["enable_calc_percent"] = self.atalho_calculadora_ativo.get()
        salvar_configuracoes(self.configuracoes)

    def _procurar_arquivo(self):
        caminho_arquivo = filedialog.askopenfilename(
            title="Selecione executável",
            filetypes=[("Executáveis", "*.exe"), ("Todos os arquivos", "*.*")]
        )

        if caminho_arquivo:
            caminho_normalizado = os.path.normpath(caminho_arquivo)
            self.campo_comando.delete(0, tk.END)
            self.campo_comando.insert(0, caminho_normalizado)

    def _atualizar_lista_monitores(self):
        self.lista_widget_monitores.delete(0, tk.END)
        for monitor in self.lista_monitores:
            prioridade_exibicao = PRIORIDADE_INTERNO_PARA_EXIBICAO.get(
                monitor['priority'],
                monitor['priority']
            )

            texto_monitor = (
                f"{monitor['process']} | {prioridade_exibicao} | "
                f"On:{monitor['power_on']} | Off:{monitor['power_off']}"
            )
            self.lista_widget_monitores.insert(tk.END, texto_monitor)

    def _adicionar_monitor(self):
        nome_processo = self.campo_processo.get().strip()

        if not nome_processo:
            messagebox.showwarning("Atenção", "Informe o nome do processo")
            return

        prioridade_exibicao = self.combo_prioridade.get()
        prioridade_interna = PRIORIDADE_EXIBICAO_PARA_INTERNO[prioridade_exibicao]
        plano_iniciar = self.combo_plano_iniciar.get()
        plano_parar = self.combo_plano_parar.get()

        novo_monitor = {
            "process": nome_processo,
            "priority": prioridade_interna,
            "power_on": plano_iniciar,
            "power_off": plano_parar
        }

        self.lista_monitores.append(novo_monitor)

        self.configuracoes["monitores"] = self.lista_monitores
        salvar_configuracoes(self.configuracoes)

        self.campo_processo.delete(0, tk.END)

        self._atualizar_lista_monitores()

    def _remover_monitor(self):
        selecao = self.lista_widget_monitores.curselection()
        if not selecao:
            messagebox.showinfo(
                "Informação", "Selecione um monitor para remover")
            return

        indice = selecao[0]
        del self.lista_monitores[indice]

        self.configuracoes["monitores"] = self.lista_monitores
        salvar_configuracoes(self.configuracoes)

        self._atualizar_lista_monitores()

def abrir_configurador(icone=None, item=None):
    def _executar():
        aplicacao = InterfaceConfigurador(DEFAULT_CONFIG)
        aplicacao.mainloop()
    threading.Thread(target=_executar, daemon=True).start()

def criar_icone_system_tray():
    try:
        caminho_icone = os.path.join(DIRETORIO_ICONES, 'icon.ico')
        imagem_icone = Image.open(caminho_icone)
        
        menu_contexto = Menu(
            MenuItem('Opções', abrir_configurador),
            MenuItem('Sair', lambda icone, item: icone.stop())
        )
        
        Icon('Atalhos', imagem_icone, 'Atalhos', menu_contexto).run()
        
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    gerenciador_energia = GerenciadorEnergia()
    thread_energia = threading.Thread(
        target=gerenciador_energia.monitorar_processos, 
        daemon=True
    )
    thread_energia.start()
    
    gerenciador_atalhos = GerenciadorAtalhos()
    gerenciador_atalhos.iniciar_monitoramento()
    
    criar_icone_system_tray()