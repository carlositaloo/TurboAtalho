# main.py (atalhos & power manager) - VERSÃO SIMPLIFICADA

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
from pystray import Icon, MenuItem, Menu
from PIL import Image

from defaults import DEFAULT_CONFIG

# Configuração do diretório de config no %APPDATA%
APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
CONFIG_DIR = os.path.join(APPDATA, 'TurboAtalho')
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, 'config.json')

# Garante que o diretório existe
os.makedirs(CONFIG_DIR, exist_ok=True)

# Caminhos e configurações principais
DIRETORIO_ATUAL = os.path.dirname(__file__)

# Configurações de monitoramento e timing
INTERVALO_MONITORAMENTO = 2    # Intervalo em segundos para verificar processos
TEMPO_DUPLO_CLIQUE = 0.5    # Tempo máximo entre pressões para atalho duplo

# Controlador do teclado para enviar teclas programaticamente
controlador_teclado = Controller()

# Mapeamento de prioridades para psutil (Windows)
MAPA_PRIORIDADES = {
    "Normal": psutil.NORMAL_PRIORITY_CLASS,
    "Acima do normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "Alta":   psutil.HIGH_PRIORITY_CLASS
}

# GUIDs dos planos de energia fixos (apenas os 3 básicos que funcionam sempre)
PLANOS_ENERGIA_FIXOS = {
    "Alto desempenho":      "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "Equilibrado":          "381b4222-f694-41f0-9685-ff5bb260df2e",
    "Economia de energia":  "a1841308-3541-4fab-bc81-f71556f20b4a"
}

# Flag para criar nova janela de console no Windows
FLAG_NOVA_JANELA = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0


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
        self.atalho_calculadora_ativo = configuracoes.get(
            "enable_calc_percent", True)

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
                self.atalho_calculadora_ativo = configuracoes.get(
                    "enable_calc_percent", True)
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
                # Reset para evitar triplo
                self.historico_teclas[chave_atalho] = None
            else:
                # Primeira pressão - salva timestamp
                self.historico_teclas[chave_atalho] = tempo_atual

    def iniciar_monitoramento(self):
        """
        Inicia o listener de teclado em thread separada.
        """
        Listener(on_press=self.ao_pressionar_tecla).start()


class GerenciadorPlanoEnergia:
    """
    Classe para gerenciar planos de energia considerando prioridades e múltiplos processos.

    Hierarquia de prioridade (do maior para menor):
    1. Alto desempenho
    2. Equilibrado  
    3. Economia de energia
    """

    PRIORIDADE_PLANOS = {
        "Alto desempenho": 3,
        "Equilibrado": 2,
        "Economia de energia": 1
    }

    def __init__(self):
        self.plano_atual = None
        self.processos_ativos = {}  # {nome_processo: config_processo}
        
        # Debug: mostra planos disponíveis
        print("🔧 GerenciadorPlanoEnergia inicializado com planos fixos:")
        for nome, guid in PLANOS_ENERGIA_FIXOS.items():
            print(f"  {nome} → {guid}")

    def adicionar_processo_ativo(self, nome_processo, config_processo):
        """
        Adiciona um processo à lista de ativos e recalcula o plano necessário.

        Args:
            nome_processo (str): Nome do processo
            config_processo (dict): Configuração do processo
        """
        print(f"🟢 Processo INICIADO: {nome_processo}")
        print(f"   Configuração: {config_processo}")
        
        self.processos_ativos[nome_processo] = config_processo
        self._aplicar_plano_necessario()

    def remover_processo_ativo(self, nome_processo):
        """
        Remove um processo da lista de ativos e recalcula o plano necessário.

        Args:
            nome_processo (str): Nome do processo a remover
        """
        if nome_processo in self.processos_ativos:
            print(f"🔴 Processo PARADO: {nome_processo}")
            del self.processos_ativos[nome_processo]
        self._aplicar_plano_necessario()

    def _obter_plano_maior_prioridade(self):
        """
        Determina qual plano de energia deve ser usado baseado nos processos ativos.

        Returns:
            str: Nome do plano de energia com maior prioridade, ou "Equilibrado" se nenhum processo ativo
        """
        if not self.processos_ativos:
            return "Equilibrado"  # Plano padrão quando nenhum processo monitorado está ativo

        maior_prioridade = 0
        plano_necessario = "Equilibrado"

        for config_processo in self.processos_ativos.values():
            plano_on = config_processo['power_on']
            prioridade = self.PRIORIDADE_PLANOS.get(plano_on, 0)

            if prioridade > maior_prioridade:
                maior_prioridade = prioridade
                plano_necessario = plano_on

        print(f"🔍 Plano necessário calculado: {plano_necessario} (prioridade {maior_prioridade})")
        return plano_necessario

    def _aplicar_plano_necessario(self):
        """
        Aplica o plano de energia necessário baseado nos processos ativos.
        """
        plano_necessario = self._obter_plano_maior_prioridade()

        # Só muda o plano se for diferente do atual
        if self.plano_atual != plano_necessario:
            print(f"⚡ Mudando plano: {self.plano_atual or 'desconhecido'} → {plano_necessario}")
            sucesso = self._definir_plano_energia(plano_necessario)
            if sucesso:
                self.plano_atual = plano_necessario
                print(f"✅ Plano alterado com sucesso para: {plano_necessario}")
            else:
                print(f"❌ Falha ao alterar para: {plano_necessario}")
        else:
            print(f"ℹ️ Plano já está correto: {plano_necessario}")

    def _definir_plano_energia(self, nome_plano):
        """
        Define o plano de energia do sistema usando GUIDs fixos.

        Args:
            nome_plano (str): Nome do plano de energia a ser aplicado
            
        Returns:
            bool: True se sucesso, False se falhou
        """
        # Usa apenas os planos fixos - sem detecção dinâmica
        guid_plano = PLANOS_ENERGIA_FIXOS.get(nome_plano)

        if not guid_plano:
            print(f"❌ Plano '{nome_plano}' não está nos planos fixos suportados")
            return False

        try:
            print(f"🔧 Executando: powercfg -setactive {guid_plano}")
            subprocess.run(
                ["powercfg", "-setactive", guid_plano],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao executar powercfg: {e}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            return False


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

        # Gerenciador de planos de energia (agora simplificado)
        self.gerenciador_plano = GerenciadorPlanoEnergia()

        # Inicializa estado dos processos verificando se já estão rodando
        self.estado_processos = {}
        
        print("🔍 Inicializando monitoramento de processos...")
        print(f"   Processos configurados: {len(self.processos_monitorados)}")
        
        for processo in self.processos_monitorados:
            nome_processo = processo['process'].lower()
            processos_ativos = [
                p for p in psutil.process_iter(['name'])
                if (p.info['name'] and
                    p.info['name'].lower().startswith(nome_processo))
            ]

            self.estado_processos[nome_processo] = bool(processos_ativos)
            
            print(f"   {nome_processo}: {'🟢 ATIVO' if processos_ativos else '⚫ PARADO'}")

            # Se processo já está ativo, adiciona ao gerenciador
            if processos_ativos:
                self.gerenciador_plano.adicionar_processo_ativo(
                    nome_processo, processo)

    def recarregar_se_necessario(self):
        """
        Verifica se as configurações foram modificadas e recarrega se necessário.
        """
        try:
            timestamp_atual = os.path.getmtime(ARQUIVO_CONFIG)
            if timestamp_atual != self.timestamp_config:
                print("🔄 Configurações modificadas, recarregando...")
                # Recarrega configurações
                configuracoes = carregar_configuracoes()
                self.processos_monitorados = configuracoes["monitores"]
                self.timestamp_config = timestamp_atual

                # Reinicializa estado dos processos
                old_estado = self.estado_processos.copy()
                self.estado_processos = {
                    processo['process'].lower(): False
                    for processo in self.processos_monitorados
                }

                # Limpa processos ativos no gerenciador para reprocessar
                self.gerenciador_plano.processos_ativos.clear()

                # Reprocessa processos que estavam ativos
                for config_processo in self.processos_monitorados:
                    nome_processo = config_processo['process'].lower()
                    if old_estado.get(nome_processo, False):
                        # Verifica se ainda está ativo
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
            # Mantém configurações atuais se houver erro
            pass

    def monitorar_processos(self):
        """
        Loop principal de monitoramento de processos.

        Executa continuamente verificando se os processos configurados
        estão ativos e ajusta planos de energia/prioridades conforme necessário.
        """
        print("🚀 Iniciando loop de monitoramento...")
        
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

                    # Processo foi iniciado
                    if processo_ativo and not self.estado_processos.get(nome_processo, False):
                        # Adiciona processo ao gerenciador (que vai calcular o plano necessário)
                        self.gerenciador_plano.adicionar_processo_ativo(
                            nome_processo, config_processo)

                        # Ajusta prioridade dos processos encontrados
                        for processo in processos_encontrados:
                            try:
                                prioridade = MAPA_PRIORIDADES.get(
                                    config_processo['priority'],
                                    psutil.NORMAL_PRIORITY_CLASS
                                )
                                processo.nice(prioridade)
                                print(f"🔧 Prioridade ajustada para {processo.info['name']}: {config_processo['priority']}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Processo pode ter terminado ou sem permissão
                                continue

                        self.estado_processos[nome_processo] = True

                    # Processo foi encerrado
                    elif not processo_ativo and self.estado_processos.get(nome_processo, False):
                        # Remove processo do gerenciador (que vai recalcular o plano necessário)
                        self.gerenciador_plano.remover_processo_ativo(
                            nome_processo)

                        self.estado_processos[nome_processo] = False

            except Exception as e:
                # Em caso de erro geral, continua monitoramento
                print(f"⚠️ Erro no monitoramento: {e}")
                pass

            # Aguarda próxima verificação
            time.sleep(INTERVALO_MONITORAMENTO)


def abrir_configurador(icone, item):
    """
    Abre a interface de configuração.
    """

    script_python = os.path.join(DIRETORIO_ATUAL, 'gui_configurador.py')

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
        caminho_icone = os.path.join(
            os.path.dirname(__file__), 'icons', 'icon.ico')
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
    print("🚀 Iniciando TurboAtalho - Versão Simplificada (3 planos)")
    
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