# main.py (atalhos & power manager)

import json
import os
import sys
import threading
import time
import subprocess
import psutil
import re
import ctypes

from pynput.keyboard import Key, KeyCode, Listener, Controller
from pystray            import Icon, MenuItem, Menu
from PIL                import Image

from defaults import DEFAULT_CONFIG

<<<<<<< HEAD
# Configuração do diretório de config no %APPDATA%
APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
CONFIG_DIR = os.path.join(APPDATA, 'TurboAtalho')
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, 'config.json')
=======
HERE         = os.path.dirname(__file__)
CONFIG_FILE  = os.path.join(HERE, 'config.json')
MON_INTERVAL = 2
DOUBLE_INT   = 0.5
>>>>>>> 2ecb76c2f7141caaf82ebf8123c9b752ff038071

# Garante que o diretório existe
os.makedirs(CONFIG_DIR, exist_ok=True)

# Caminhos e configurações principais
DIRETORIO_ATUAL = os.path.dirname(__file__)

# Configurações de monitoramento e timing
INTERVALO_MONITORAMENTO = 30    # Intervalo em segundos para verificar processos
TEMPO_DUPLO_CLIQUE     = 0.5    # Tempo máximo entre pressões para atalho duplo

# Determina o diretório base (PyInstaller ou desenvolvimento)
if getattr(sys, 'frozen', False):
    # Se executado via PyInstaller --onefile, recursos ficam em _MEIPASS
    DIRETORIO_BASE = sys._MEIPASS
else:
    # Modo desenvolvimento - diretório do script
    DIRETORIO_BASE = os.path.dirname(__file__)

DIRETORIO_ICONES = os.path.join(DIRETORIO_BASE, 'icons')

# Controlador do teclado para enviar teclas programaticamente
controlador_teclado = Controller()

# Mapeamento de prioridades para psutil (Windows)
MAPA_PRIORIDADES = {
    "Normal": psutil.NORMAL_PRIORITY_CLASS,
    "High":   psutil.HIGH_PRIORITY_CLASS
}

# GUIDs dos planos de energia padrão do Windows (em minúsculas para comparação)
PLANOS_ENERGIA_PADRAO = {
    "Alto desempenho":      "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c".lower(),
    "Equilibrado":          "381b4222-f694-41f0-9685-ff5bb260df2e".lower(),
    "Economia de energia":  "a1841308-3541-4fab-bc81-f71556f20b4a".lower()
}

# Flag para criar nova janela de console no Windows
FLAG_NOVA_JANELA = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0


def obter_guids_planos_energia():
    """
    Obtém os GUIDs dos planos de energia disponíveis no sistema atual.
    
    Returns:
        dict: Mapeamento nome_plano → guid_lowercase dos planos disponíveis
    """
    try:
        resultado = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        # Se falhar, retorna dicionário vazio (usará fallbacks)
        return {}
    
    mapeamento_planos = {}
    for linha in resultado.stdout.splitlines():
        # Procura padrão: GUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (Nome do Plano)
        match = re.search(r"GUID:\s*([0-9A-Fa-f-]+)\s*\((.+?)\)", linha)
        if match:
            guid = match.group(1).lower()
            nome = match.group(2).strip()
            mapeamento_planos[nome] = guid
    
    return mapeamento_planos


def obter_titulo_janela_ativa():
    """
    Obtém o título da janela atualmente em foco no Windows.
    
    Returns:
        str: Título da janela ativa
    """
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        tamanho = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(tamanho + 1)
        user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
        return buffer.value
    except Exception:
        # Se falhar, retorna string vazia
        return ""


def carregar_configuracoes():
    """
    Carrega as configurações do arquivo JSON ou cria com padrões se não existir.
    
    Returns:
        dict: Configurações carregadas
    """
    if not os.path.exists(ARQUIVO_CONFIG):
        # Cria arquivo de configuração com valores padrão
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as arquivo:
            json.dump(DEFAULT_CONFIG, arquivo, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, FileNotFoundError):
        # Se arquivo corrompido, retorna configurações padrão
        return DEFAULT_CONFIG.copy()


def executar_comando(comando):
    """
    Executa um comando no sistema.
    
    - Se for arquivo executável (.exe): abre em nova janela de console
    - Caso contrário: executa no shell atual
    
    Args:
        comando (str): Comando ou caminho do executável a ser executado
    """
    try:
        if os.path.isfile(comando) or comando.lower().endswith('.exe'):
            # Executável - abre em nova janela
            subprocess.Popen([comando], creationflags=FLAG_NOVA_JANELA)
        else:
            # Comando shell - executa normalmente
            subprocess.Popen(comando, shell=True)
    except Exception as erro:
        # Se falhar, continua silenciosamente (aplicação em background)
        pass


class GerenciadorAtalhos:
    """
    Classe responsável por gerenciar os atalhos de teclado configuráveis.
    
    Monitora teclas pressionadas e executa comandos quando detecta
    duplo-pressionamento das teclas configuradas.
    """
    
    def __init__(self):
        configuracoes = carregar_configuracoes()
        
        # Configurações de atalhos
        self.atalhos_configurados = configuracoes["atalhos"]
        self.atalho_calculadora_ativo = configuracoes.get("enable_calc_percent", True)
        
        # Controle de modificação do arquivo
        self.timestamp_config = os.path.getmtime(ARQUIVO_CONFIG)
        
        # Histórico de teclas pressionadas (para detectar duplo-clique)
        self.historico_teclas = {}

    def recarregar_se_necessario(self):
        """
        Verifica se o arquivo de configuração foi modificado e recarrega se necessário.
        """
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                # Arquivo foi modificado - recarrega configurações
                configuracoes = carregar_configuracoes()
                self.atalhos_configurados = configuracoes["atalhos"]
                self.atalho_calculadora_ativo = configuracoes.get("enable_calc_percent", True)
                self.timestamp_config = timestamp_atual
        except OSError:
            # Se arquivo não existir ou erro de acesso, mantém configurações atuais
            pass

    def ao_pressionar_tecla(self, tecla):
        """
        Handler chamado quando uma tecla é pressionada.
        
        Args:
            tecla: Objeto Key ou KeyCode da tecla pressionada
        """
        # Atalho especial: Shift direito na Calculadora envia '%'
        if (self.atalho_calculadora_ativo and 
            tecla == Key.shift_r and 
            obter_titulo_janela_ativa() == "Calculadora"):
            
            # Simula Shift+5 para enviar '%'
            controlador_teclado.press(Key.shift)
            controlador_teclado.press('5')
            controlador_teclado.release('5')
            controlador_teclado.release(Key.shift)
            return

        # Verifica atalhos configuráveis (duplo-pressionamento)
        self.recarregar_se_necessario()
        tempo_atual = time.time()
        
        for atalho in self.atalhos_configurados:
            # Converte string da configuração para objeto tecla
            try:
                tecla_configurada = eval(atalho['tecla'])
            except (NameError, SyntaxError):
                # Se eval falhar, usa como string literal
                tecla_configurada = atalho['tecla']
            
            # Verifica se a tecla pressionada corresponde à configurada
            tecla_corresponde = (
                tecla == tecla_configurada or
                (isinstance(tecla, KeyCode) and 
                 getattr(tecla, 'char', None) == tecla_configurada)
            )
            
            if not tecla_corresponde:
                continue
            
            # Verifica duplo-pressionamento
            chave_atalho = atalho['tecla']
            tempo_anterior = self.historico_teclas.get(chave_atalho)
            
            if tempo_anterior and (tempo_atual - tempo_anterior) < TEMPO_DUPLO_CLIQUE:
                # Duplo-pressionamento detectado - executa comando
                executar_comando(atalho['comando'])
                self.historico_teclas[chave_atalho] = None  # Reset para evitar triplo
            else:
                # Primeira pressão - salva timestamp
                self.historico_teclas[chave_atalho] = tempo_atual

    def iniciar_monitoramento(self):
        """
        Inicia o listener de teclado em thread separada.
        """
        Listener(on_press=self.ao_pressionar_tecla).start()


class GerenciadorEnergia:
    """
    Classe responsável por monitorar processos e ajustar automaticamente
    os planos de energia e prioridades baseado nos processos em execução.
    """
    
    def __init__(self):
        configuracoes = carregar_configuracoes()
        
        # Configurações de monitoramento
        self.processos_monitorados = configuracoes["monitores"]
        self.timestamp_config = os.path.getmtime(ARQUIVO_CONFIG)
        
        # Mapeamento de planos de energia disponíveis no sistema
        self.mapa_planos_sistema = obter_guids_planos_energia()
        
        # Estado atual dos processos (True = ativo, False = inativo)
        self.estado_processos = {
            processo['process'].lower(): False 
            for processo in self.processos_monitorados
        }

    def recarregar_se_necessario(self):
        """
        Verifica se as configurações foram modificadas e recarrega se necessário.
        """
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                # Recarrega configurações
                configuracoes = carregar_configuracoes()
                self.processos_monitorados = configuracoes["monitores"]
                self.timestamp_config = timestamp_atual
                self.mapa_planos_sistema = obter_guids_planos_energia()
                
                # Reinicializa estado dos processos
                self.estado_processos = {
                    processo['process'].lower(): False 
                    for processo in self.processos_monitorados
                }
        except OSError:
            # Mantém configurações atuais se houver erro
            pass

    def monitorar_processos(self):
        """
        Loop principal de monitoramento de processos.
        
        Executa continuamente verificando se os processos configurados
        estão ativos e ajusta planos de energia/prioridades conforme necessário.
        """
        while True:
            try:
                self.recarregar_se_necessario()
                
                for config_processo in self.processos_monitorados:
                    nome_processo = config_processo['process'].lower()
                    
                    # Busca processos que começam com o nome configurado
                    processos_encontrados = [
                        processo for processo in psutil.process_iter(['name'])
                        if (processo.info['name'] and 
                            processo.info['name'].lower().startswith(nome_processo))
                    ]
                    
                    processo_ativo = bool(processos_encontrados)
                    
                    # Obtém GUIDs dos planos de energia (com fallbacks)
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
                    
                    # Processo foi iniciado
                    if processo_ativo and not self.estado_processos[nome_processo]:
                        # Altera plano de energia para modo de alta performance
                        try:
                            subprocess.run(
                                ["powercfg", "-setactive", guid_plano_ativo], 
                                check=True
                            )
                        except subprocess.CalledProcessError:
                            # Se falhar, continua (pode não ter permissões)
                            pass
                        
                        # Ajusta prioridade dos processos encontrados
                        for processo in processos_encontrados:
                            try:
                                prioridade = MAPA_PRIORIDADES.get(
                                    config_processo['priority'], 
                                    psutil.NORMAL_PRIORITY_CLASS
                                )
                                processo.nice(prioridade)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Processo pode ter terminado ou sem permissão
                                continue
                        
                        self.estado_processos[nome_processo] = True
                    
                    # Processo foi encerrado
                    elif not processo_ativo and self.estado_processos[nome_processo]:
                        # Retorna ao plano de energia padrão
                        try:
                            subprocess.run(
                                ["powercfg", "-setactive", guid_plano_inativo], 
                                check=True
                            )
                        except subprocess.CalledProcessError:
                            # Se falhar, continua
                            pass
                        
                        self.estado_processos[nome_processo] = False
                
            except Exception:
                # Em caso de erro geral, continua monitoramento
                pass
            
            # Aguarda próxima verificação
            time.sleep(INTERVALO_MONITORAMENTO)


def abrir_configurador(icone, item):
    """
    Abre a interface de configuração.
    
    Tenta abrir o executável compilado primeiro, senão executa o script Python.
    """
    executavel = os.path.join(DIRETORIO_ATUAL, 'gui_configurator.exe')
    script_python = os.path.join(DIRETORIO_ATUAL, 'gui_configurator.py')
    
    if os.path.exists(executavel):
        argumentos = [executavel]
    else:
        argumentos = [sys.executable, script_python]
    
    try:
        subprocess.Popen(argumentos)
    except Exception:
        # Se falhar, continua silenciosamente
        pass


def criar_icone_system_tray():
    """
    Cria e executa o ícone na bandeja do sistema (system tray).
    """
    try:
        # Carrega ícone
        caminho_icone = os.path.join(DIRETORIO_ICONES, 'icon.ico')
        imagem_icone = Image.open(caminho_icone)
        
        # Cria menu de contexto
        menu_contexto = Menu(
            MenuItem('Opções', abrir_configurador),
            MenuItem('Sair', lambda icone, item: icone.stop())
        )
        
        # Cria e executa ícone do system tray
        Icon('Atalhos', imagem_icone, 'Atalhos', menu_contexto).run()
        
    except Exception:
        # Se falhar ao criar tray, termina aplicação
        sys.exit(1)


if __name__ == "__main__":
    # Inicia gerenciador de energia em thread separada
    gerenciador_energia = GerenciadorEnergia()
    thread_energia = threading.Thread(
        target=gerenciador_energia.monitorar_processos, 
        daemon=True
    )
    thread_energia.start()
    
    # Inicia gerenciador de atalhos
    gerenciador_atalhos = GerenciadorAtalhos()
    gerenciador_atalhos.iniciar_monitoramento()
    
    # Cria interface de system tray (bloqueia thread principal)
    criar_icone_system_tray()