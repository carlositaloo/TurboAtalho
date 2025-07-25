import json
import os
import sys
import threading
import time
import subprocess
import psutil
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from pynput.keyboard import Key, KeyCode, Listener, Controller
from pystray import Icon, MenuItem, Menu
from PIL import Image

# Detecta se está rodando como executável empacotado
if getattr(sys, 'frozen', False):
    # Rodando como executável
    BASE_DIR = os.path.dirname(sys.executable)
    SCRIPT_DIR = sys._MEIPASS  # Diretório temporário do PyInstaller
else:
    # Rodando como script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_DIR = BASE_DIR

APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
CONFIG_DIR = os.path.join(APPDATA, 'TurboAtalho')
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, 'config.json')

os.makedirs(CONFIG_DIR, exist_ok=True)

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

OPCOES_PRIORIDADE_EXIBICAO = ["Normal", "Acima do normal", "Alta"]

PRIORIDADE_EXIBICAO_PARA_INTERNO = {
    "Normal": "Normal", "Acima do normal": "Acima do normal", "Alta": "Alta"}
PRIORIDADE_INTERNO_PARA_EXIBICAO = {
    valor: chave for chave, valor in PRIORIDADE_EXIBICAO_PARA_INTERNO.items()}

OPCOES_PLANOS_ENERGIA = [
    "Alto desempenho",
    "Equilibrado",
    "Economia de energia"
]

INTERVALO_MONITORAMENTO = 2
TEMPO_DUPLO_CLIQUE = 0.5

controlador_teclado = Controller()

MAPA_PRIORIDADES = {
    "Normal": psutil.NORMAL_PRIORITY_CLASS,
    "Acima do normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "Alta":   psutil.HIGH_PRIORITY_CLASS
}

PLANOS_ENERGIA_FIXOS = {
    "Alto desempenho":      "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "Equilibrado":          "381b4222-f694-41f0-9685-ff5bb260df2e",
    "Economia de energia":  "a1841308-3541-4fab-bc81-f71556f20b4a"
}

FLAG_NOVA_JANELA = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0

def obter_caminho_recurso(caminho_relativo):
    """Obtém o caminho correto para recursos, seja rodando como script ou exe"""
    try:
        # Primeiro tenta no diretório do executável/script
        caminho_base = os.path.join(BASE_DIR, caminho_relativo)
        if os.path.exists(caminho_base):
            return caminho_base
        
        # Se não encontrar, tenta no diretório temporário do PyInstaller
        caminho_temp = os.path.join(SCRIPT_DIR, caminho_relativo)
        if os.path.exists(caminho_temp):
            return caminho_temp
        
        # Fallback: retorna o caminho original
        return caminho_relativo
    except:
        return caminho_relativo

def carregar_configuracoes(configuracao_padrao):
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

def carregar_configuracoes_main():
    if not os.path.exists(ARQUIVO_CONFIG):
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as arquivo:
            json.dump(DEFAULT_CONFIG, arquivo, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()

    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_CONFIG.copy()

def executar_comando(comando):
    try:
        if os.path.isfile(comando) or comando.lower().endswith('.exe'):
            subprocess.Popen([comando], creationflags=FLAG_NOVA_JANELA)
        else:
            subprocess.Popen(comando, shell=True)
    except Exception as erro:
        pass

class InterfaceConfigurador(tk.Tk):
    PLACEHOLDER_TECLA = "Clique e pressione tecla"

    def __init__(self, configuracao_padrao):
        super().__init__()
        self._configurar_janela()
        self._inicializar_dados(configuracao_padrao)
        self._construir_interface()

    def _configurar_janela(self):
        # Tenta carregar o ícone com tratamento de erro melhorado
        caminho_icone = obter_caminho_recurso(os.path.join('icons', 'icon.ico'))
        if os.path.exists(caminho_icone):
            try:
                self.iconbitmap(caminho_icone)
            except (tk.TclError, Exception):
                pass  # Ignora erro de ícone

        self.title("Opções Turbo Atalho")
        self.geometry("230x300")
        self.resizable(False, False)

    def _inicializar_dados(self, configuracao_padrao):
        self.configuracoes = carregar_configuracoes(configuracao_padrao)
        self.lista_atalhos = self.configuracoes["atalhos"]
        self.lista_monitores = self.configuracoes["monitores"]
        
        self._limpar_monitores_invalidos()

        self.atalho_calculadora_ativo = tk.BooleanVar(
            value=self.configuracoes.get("enable_calc_percent", True)
        )

    def _limpar_monitores_invalidos(self):
        monitores_validos = []
        for monitor in self.lista_monitores:
            power_on = monitor.get('power_on', '')
            power_off = monitor.get('power_off', '')
            
            if power_on in OPCOES_PLANOS_ENERGIA and power_off in OPCOES_PLANOS_ENERGIA:
                monitores_validos.append(monitor)
        
        if len(monitores_validos) != len(self.lista_monitores):
            self.lista_monitores = monitores_validos
            self.configuracoes["monitores"] = monitores_validos
            salvar_configuracoes(self.configuracoes)
            
            messagebox.showinfo(
                "Limpeza de Configuração",
                f"Alguns monitores com planos não suportados foram removidos.\n"
                f"Suporta apenas:\n"
                f"• Alto desempenho\n• Equilibrado\n• Economia de energia"
            )

    def _construir_interface(self):
        frame_principal = ttk.Frame(self)
        frame_principal.pack(fill="both", expand=True, padx=3, pady=3)

        frame_principal.columnconfigure(0, weight=1)
        frame_principal.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(frame_principal)
        notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        self._construir_aba_atalhos(notebook)
        self._construir_aba_energia(notebook)

        ttk.Button(frame_principal, text="Fechar", command=self.destroy)\
            .grid(row=1, column=0, sticky="e", pady=(5, 0))

    def _construir_aba_atalhos(self, notebook):
        aba = ttk.Frame(notebook)
        notebook.add(aba, text="Gerenciar Atalhos")
        aba.columnconfigure(1, weight=1)
        aba.rowconfigure(4, weight=1)

        ttk.Label(aba, text="Tecla:")\
            .grid(row=0, column=0, sticky='w', padx=2, pady=1)

        self.campo_tecla = ttk.Entry(aba)
        self.campo_tecla.grid(row=0, column=1, columnspan=2,
                              sticky='ew', padx=2, pady=1)
        self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.campo_tecla.bind("<FocusIn>", self._ao_focar_campo_tecla)
        self.campo_tecla.bind("<FocusOut>", self._ao_desfocar_campo_tecla)

        ttk.Label(aba, text="Comando:")\
            .grid(row=1, column=0, sticky='w', padx=2, pady=1)

        self.campo_comando = ttk.Entry(aba)
        self.campo_comando.grid(row=1, column=1, sticky='ew', padx=2, pady=1)

        ttk.Button(aba, text="…", width=3, command=self._procurar_arquivo)\
            .grid(row=1, column=2, padx=2, pady=1)

        ttk.Button(aba, text="Remover", command=self._remover_atalho)\
            .grid(row=2, column=0, padx=2, pady=3, sticky='w')
        ttk.Button(aba, text="Adicionar", command=self._adicionar_atalho)\
            .grid(row=2, column=1, columnspan=2, padx=2, pady=3, sticky='e')

        checkbox_calculadora = ttk.Checkbutton(
            aba,
            text="'%' na Calculadora",
            variable=self.atalho_calculadora_ativo,
            command=self._alternar_atalho_calculadora
        )
        checkbox_calculadora.grid(
            row=3, column=0, columnspan=3, sticky='w', padx=2, pady=3)

        self.lista_widget_atalhos = tk.Listbox(aba, height=6)
        self.lista_widget_atalhos.grid(
            row=4, column=0, columnspan=3, sticky='nsew', padx=2, pady=1)

        self._atualizar_lista_atalhos()

    def _construir_aba_energia(self, notebook):
        aba = ttk.Frame(notebook)
        notebook.add(aba, text="Gerenciar Energia")
        aba.columnconfigure(1, weight=1)
        aba.rowconfigure(6, weight=1)

        ttk.Label(aba, text="Processo:")\
            .grid(row=1, column=0, sticky='w', padx=2, pady=1)

        self.campo_processo = ttk.Entry(aba)
        self.campo_processo.grid(row=1, column=1, sticky='ew', padx=2, pady=1)

        ttk.Label(aba, text="Prioridade:")\
            .grid(row=2, column=0, sticky='w', padx=2, pady=1)

        self.combo_prioridade = ttk.Combobox(
            aba,
            values=OPCOES_PRIORIDADE_EXIBICAO,
            state='readonly'
        )
        self.combo_prioridade.grid(
            row=2, column=1, sticky='ew', padx=2, pady=1)
        self.combo_prioridade.set(
            OPCOES_PRIORIDADE_EXIBICAO[2])

        ttk.Label(aba, text="Ao Iniciar:")\
            .grid(row=3, column=0, sticky='w', padx=2, pady=1)

        self.combo_plano_iniciar = ttk.Combobox(
            aba,
            values=OPCOES_PLANOS_ENERGIA,
            state='readonly'
        )
        self.combo_plano_iniciar.grid(
            row=3, column=1, sticky='ew', padx=2, pady=1)
        self.combo_plano_iniciar.set(
            OPCOES_PLANOS_ENERGIA[0])

        ttk.Label(aba, text="Ao Parar:")\
            .grid(row=4, column=0, sticky='w', padx=2, pady=1)

        self.combo_plano_parar = ttk.Combobox(
            aba,
            values=OPCOES_PLANOS_ENERGIA,
            state='readonly'
        )
        self.combo_plano_parar.grid(
            row=4, column=1, sticky='ew', padx=2, pady=1)
        self.combo_plano_parar.set(OPCOES_PLANOS_ENERGIA[1])

        ttk.Button(aba, text="Remover", command=self._remover_monitor)\
            .grid(row=5, column=0, padx=2, pady=3, sticky='w')
        ttk.Button(aba, text="Adicionar", command=self._adicionar_monitor)\
            .grid(row=5, column=1, padx=2, pady=3, sticky='e')

        self.lista_widget_monitores = tk.Listbox(aba, height=6)
        self.lista_widget_monitores.grid(
            row=6, column=0, columnspan=3, sticky='nsew', padx=2, pady=1)

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

        if plano_iniciar not in OPCOES_PLANOS_ENERGIA:
            messagebox.showerror("Erro", f"Plano '{plano_iniciar}' não é suportado.")
            return
        
        if plano_parar not in OPCOES_PLANOS_ENERGIA:
            messagebox.showerror("Erro", f"Plano '{plano_parar}' não é suportado.")
            return

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

class GerenciadorAtalhos:
    def __init__(self):
        configuracoes = carregar_configuracoes_main()

        self.atalhos_configurados = configuracoes["atalhos"]
        self.atalho_calculadora_ativo = configuracoes.get(
            "enable_calc_percent", True)

        self.timestamp_config = os.path.getmtime(ARQUIVO_CONFIG)
        self.historico_teclas = {}

    def recarregar_se_necessario(self):
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                configuracoes = carregar_configuracoes_main()
                self.atalhos_configurados = configuracoes["atalhos"]
                self.atalho_calculadora_ativo = configuracoes.get(
                    "enable_calc_percent", True)
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

class GerenciadorPlanoEnergia:
    PRIORIDADE_PLANOS = {
        "Alto desempenho": 3,
        "Equilibrado": 2,
        "Economia de energia": 1
    }

    def __init__(self):
        self.plano_atual = None
        self.processos_ativos = {}

    def adicionar_processo_ativo(self, nome_processo, config_processo):
        self.processos_ativos[nome_processo] = config_processo
        self._aplicar_plano_necessario()

    def remover_processo_ativo(self, nome_processo):
        if nome_processo in self.processos_ativos:
            del self.processos_ativos[nome_processo]
        self._aplicar_plano_necessario()

    def _obter_plano_maior_prioridade(self):
        if not self.processos_ativos:
            return "Equilibrado"

        maior_prioridade = 0
        plano_necessario = "Equilibrado"

        for config_processo in self.processos_ativos.values():
            plano_on = config_processo['power_on']
            prioridade = self.PRIORIDADE_PLANOS.get(plano_on, 0)

            if prioridade > maior_prioridade:
                maior_prioridade = prioridade
                plano_necessario = plano_on

        return plano_necessario

    def _aplicar_plano_necessario(self):
        plano_necessario = self._obter_plano_maior_prioridade()

        if self.plano_atual != plano_necessario:
            sucesso = self._definir_plano_energia(plano_necessario)
            if sucesso:
                self.plano_atual = plano_necessario

    def _definir_plano_energia(self, nome_plano):
        guid_plano = PLANOS_ENERGIA_FIXOS.get(nome_plano)

        if not guid_plano:
            return False

        try:
            subprocess.run(
                ["powercfg", "-setactive", guid_plano],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            return False

class GerenciadorEnergia:
    def __init__(self):
        configuracoes = carregar_configuracoes_main()

        self.processos_monitorados = configuracoes["monitores"]
        self.timestamp_config = os.path.getmtime(ARQUIVO_CONFIG)

        self.gerenciador_plano = GerenciadorPlanoEnergia()
        self.estado_processos = {}
        
        for processo in self.processos_monitorados:
            nome_processo = processo['process'].lower()
            processos_ativos = [
                p for p in psutil.process_iter(['name'])
                if (p.info['name'] and
                    p.info['name'].lower().startswith(nome_processo))
            ]

            self.estado_processos[nome_processo] = bool(processos_ativos)

            if processos_ativos:
                self.gerenciador_plano.adicionar_processo_ativo(
                    nome_processo, processo)

    def recarregar_se_necessario(self):
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                configuracoes = carregar_configuracoes_main()
                self.processos_monitorados = configuracoes["monitores"]
                self.timestamp_config = timestamp_atual

                old_estado = self.estado_processos.copy()
                self.estado_processos = {
                    processo['process'].lower(): False
                    for processo in self.processos_monitorados
                }

                self.gerenciador_plano.processos_ativos.clear()

                for config_processo in self.processos_monitorados:
                    nome_processo = config_processo['process'].lower()
                    if old_estado.get(nome_processo, False):
                        processos_encontrados = [
                            processo for processo in psutil.process_iter(['name'])
                            if (processo.info['name'] and
                                processo.info['name'].lower().startswith(nome_processo))
                        ]

                        if processos_encontrados:
                            self.estado_processos[nome_processo] = True
                            self.gerenciador_plano.adicionar_processo_ativo(
                                nome_processo, config_processo)

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

                    if processo_ativo and not self.estado_processos.get(nome_processo, False):
                        self.gerenciador_plano.adicionar_processo_ativo(
                            nome_processo, config_processo)

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

                    elif not processo_ativo and self.estado_processos.get(nome_processo, False):
                        self.gerenciador_plano.remover_processo_ativo(
                            nome_processo)

                        self.estado_processos[nome_processo] = False

            except Exception as e:
                pass

            time.sleep(INTERVALO_MONITORAMENTO)

def abrir_configurador(icone, item):
    try:
        import threading
        def criar_interface():
            aplicacao = InterfaceConfigurador(DEFAULT_CONFIG)
            aplicacao.protocol("WM_DELETE_WINDOW", aplicacao.destroy)
            aplicacao.mainloop()
        
        thread_interface = threading.Thread(target=criar_interface, daemon=True)
        thread_interface.start()
    except Exception:
        pass

def criar_icone_system_tray():
    try:
        # Usa a função melhorada para encontrar o ícone
        caminho_icone = obter_caminho_recurso(os.path.join('icons', 'icon.ico'))
        
        # Fallback para um ícone padrão se não encontrar
        if not os.path.exists(caminho_icone):
            # Cria um ícone simples em memória como fallback
            imagem_icone = Image.new('RGB', (16, 16), color='blue')
        else:
            imagem_icone = Image.open(caminho_icone)

        menu_contexto = Menu(
            MenuItem('Opções', abrir_configurador),
            MenuItem('Sair', lambda icone, item: icone.stop())
        )

        Icon('Atalhos', imagem_icone, 'Atalhos', menu_contexto).run()

    except Exception as e:
        # Se falhar completamente, tenta rodar sem ícone
        print(f"Erro ao criar ícone da system tray: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        gerenciador_energia = GerenciadorEnergia()
        thread_energia = threading.Thread(
            target=gerenciador_energia.monitorar_processos,
            daemon=True
        )
        thread_energia.start()

        gerenciador_atalhos = GerenciadorAtalhos()
        gerenciador_atalhos.iniciar_monitoramento()

        criar_icone_system_tray()
    except Exception as e:
        # Em caso de erro crítico, tenta mostrar uma mensagem
        try:
            import tkinter.messagebox as mb
            mb.showerror("Erro Fatal", f"Erro ao iniciar aplicação: {str(e)}")
        except:
            pass
        sys.exit(1)