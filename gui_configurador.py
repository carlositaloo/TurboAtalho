# gui_configurator.py - Interface de configuração para atalhos e energia

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from defaults import DEFAULT_CONFIG

# Configuração do diretório de config no %APPDATA%
APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
CONFIG_DIR = os.path.join(APPDATA, 'TurboAtalho')
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, 'config.json')

# Garante que o diretório existe
os.makedirs(CONFIG_DIR, exist_ok=True)

# Opções de prioridade para exibição na interface
OPCOES_PRIORIDADE_EXIBICAO = ["Normal", "Acima do normal", "Alta"]

# Mapeamento entre exibição e valores internos de prioridade
PRIORIDADE_EXIBICAO_PARA_INTERNO = {
    "Normal": "Normal", "Acima do normal": "Acima do normal", "Alta": "Alta"}
PRIORIDADE_INTERNO_PARA_EXIBICAO = {
    valor: chave for chave, valor in PRIORIDADE_EXIBICAO_PARA_INTERNO.items()}

# Opções de planos de energia disponíveis (apenas 3 planos que funcionam sempre)
OPCOES_PLANOS_ENERGIA = [
    "Alto desempenho",
    "Equilibrado",
    "Economia de energia"
]


def carregar_configuracoes(configuracao_padrao):
    """
    Carrega configurações do arquivo JSON ou cria com padrões se não existir.

    Args:
        configuracao_padrao (dict): Configurações padrão caso arquivo não exista

    Returns:
        dict: Configurações carregadas
    """
    if not os.path.exists(ARQUIVO_CONFIG):
        # Cria arquivo com configurações padrão
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as arquivo:
            json.dump(configuracao_padrao, arquivo,
                      indent=4, ensure_ascii=False)
        return configuracao_padrao.copy()

    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, FileNotFoundError):
        # Se arquivo corrompido, retorna configurações padrão
        return configuracao_padrao.copy()


def salvar_configuracoes(configuracoes):
    """
    Salva configurações no arquivo JSON.

    Args:
        configuracoes (dict): Configurações a serem salvas
    """
    try:
        with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as arquivo:
            json.dump(configuracoes, arquivo, indent=4, ensure_ascii=False)
    except Exception:
        # Se falhar ao salvar, mostra erro ao usuário
        messagebox.showerror(
            "Erro", "Não foi possível salvar as configurações")


class InterfaceConfigurador(tk.Tk):
    """
    Interface gráfica principal para configuração de atalhos e monitoramento de energia.

    Permite gerenciar:
    - Atalhos de teclado personalizados
    - Monitoramento de processos com ajuste automático de energia
    - Configuração especial para calculadora
    """

    # Texto placeholder para campo de tecla
    PLACEHOLDER_TECLA = "Clique e pressione tecla"

    def __init__(self, configuracao_padrao):
        super().__init__()

        # Configuração da janela principal
        self._configurar_janela()

        # Carrega configurações e inicializa variáveis
        self._inicializar_dados(configuracao_padrao)

        # Constrói interface gráfica
        self._construir_interface()

    def _configurar_janela(self):
        """
        Configura propriedades básicas da janela principal.
        """
        # Define ícone da janela (se disponível)
        caminho_icone = os.path.join(
            os.path.dirname(__file__), 'icons', 'icon.ico')
        if os.path.exists(caminho_icone):
            try:
                self.iconbitmap(caminho_icone)
            except tk.TclError:
                # Se falhar ao carregar ícone, continua sem ele
                pass

        # Propriedades da janela
        self.title("Opções Turbo Atalho")
        self.geometry("230x300")
        self.resizable(False, False)

    def _inicializar_dados(self, configuracao_padrao):
        """
        Carrega configurações e inicializa variáveis de controle.

        Args:
            configuracao_padrao (dict): Configurações padrão
        """
        # Carrega configurações do arquivo
        self.configuracoes = carregar_configuracoes(configuracao_padrao)

        # Listas de dados
        self.lista_atalhos = self.configuracoes["atalhos"]
        self.lista_monitores = self.configuracoes["monitores"]
        
        # Limpa monitores com planos não suportados
        self._limpar_monitores_invalidos()

        # Variável para checkbox da calculadora
        self.atalho_calculadora_ativo = tk.BooleanVar(
            value=self.configuracoes.get("enable_calc_percent", True)
        )

    def _limpar_monitores_invalidos(self):
        """
        Remove monitores que usam planos de energia não suportados
        """
        monitores_validos = []
        for monitor in self.lista_monitores:
            power_on = monitor.get('power_on', '')
            power_off = monitor.get('power_off', '')
            
            # Verifica se os planos são suportados
            if power_on in OPCOES_PLANOS_ENERGIA and power_off in OPCOES_PLANOS_ENERGIA:
                monitores_validos.append(monitor)
            else:
                print(f"⚠️ Removendo monitor inválido: {monitor.get('process', 'desconhecido')} "
                      f"(planos não suportados: {power_on}, {power_off})")
        
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
        """
        Constrói toda a interface gráfica da aplicação.
        """
        # Frame principal que ocupa toda a janela
        frame_principal = ttk.Frame(self)
        frame_principal.pack(fill="both", expand=True, padx=3, pady=3)

        # Configura grid do frame principal
        frame_principal.columnconfigure(0, weight=1)
        frame_principal.rowconfigure(0, weight=1)

        # Cria notebook (abas)
        notebook = ttk.Notebook(frame_principal)
        notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Constrói abas
        self._construir_aba_atalhos(notebook)
        self._construir_aba_energia(notebook)

        # Botão fechar na parte inferior
        ttk.Button(frame_principal, text="Fechar", command=self.destroy)\
            .grid(row=1, column=0, sticky="e", pady=(5, 0))

    def _construir_aba_atalhos(self, notebook):
        """
        Constrói a aba de gerenciamento de atalhos.

        Args:
            notebook: Widget Notebook onde adicionar a aba
        """
        aba = ttk.Frame(notebook)
        notebook.add(aba, text="Gerenciar Atalhos")
        # Configura expansão das colunas e linhas
        aba.columnconfigure(1, weight=1)
        aba.rowconfigure(4, weight=1)

        # Campo de entrada para tecla
        ttk.Label(aba, text="Tecla:")\
            .grid(row=0, column=0, sticky='w', padx=2, pady=1)

        self.campo_tecla = ttk.Entry(aba)
        self.campo_tecla.grid(row=0, column=1, columnspan=2,
                              sticky='ew', padx=2, pady=1)
        self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.campo_tecla.bind("<FocusIn>", self._ao_focar_campo_tecla)
        self.campo_tecla.bind("<FocusOut>", self._ao_desfocar_campo_tecla)

        # Campo de entrada para comando
        ttk.Label(aba, text="Comando:")\
            .grid(row=1, column=0, sticky='w', padx=2, pady=1)

        self.campo_comando = ttk.Entry(aba)
        self.campo_comando.grid(row=1, column=1, sticky='ew', padx=2, pady=1)

        # Botão para procurar arquivo
        ttk.Button(aba, text="…", width=3, command=self._procurar_arquivo)\
            .grid(row=1, column=2, padx=2, pady=1)

        # Botões de ação
        ttk.Button(aba, text="Remover", command=self._remover_atalho)\
            .grid(row=2, column=0, padx=2, pady=3, sticky='w')
        ttk.Button(aba, text="Adicionar", command=self._adicionar_atalho)\
            .grid(row=2, column=1, columnspan=2, padx=2, pady=3, sticky='e')

        # Checkbox para atalho especial da calculadora
        checkbox_calculadora = ttk.Checkbutton(
            aba,
            text="'%' na Calculadora",
            variable=self.atalho_calculadora_ativo,
            command=self._alternar_atalho_calculadora
        )
        checkbox_calculadora.grid(
            row=3, column=0, columnspan=3, sticky='w', padx=2, pady=3)

        # Lista de atalhos configurados
        self.lista_widget_atalhos = tk.Listbox(aba, height=6)
        self.lista_widget_atalhos.grid(
            row=4, column=0, columnspan=3, sticky='nsew', padx=2, pady=1)

        # Carrega atalhos na lista
        self._atualizar_lista_atalhos()

    def _construir_aba_energia(self, notebook):
        """
        Constrói a aba de gerenciamento de energia.

        Args:
            notebook: Widget Notebook onde adicionar a aba
        """
        aba = ttk.Frame(notebook)
        notebook.add(aba, text="Gerenciar Energia")
        # Configura expansão das colunas e linhas
        aba.columnconfigure(1, weight=1)
        aba.rowconfigure(6, weight=1)

        # Campo para nome do processo
        ttk.Label(aba, text="Processo:")\
            .grid(row=1, column=0, sticky='w', padx=2, pady=1)

        self.campo_processo = ttk.Entry(aba)
        self.campo_processo.grid(row=1, column=1, sticky='ew', padx=2, pady=1)

        # Combo para prioridade
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
            OPCOES_PRIORIDADE_EXIBICAO[2])  # "Alta" como padrão

        # Combo para plano ao iniciar processo
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
            OPCOES_PLANOS_ENERGIA[0])  # "Alto desempenho"

        # Combo para plano ao parar processo
        ttk.Label(aba, text="Ao Parar:")\
            .grid(row=4, column=0, sticky='w', padx=2, pady=1)

        self.combo_plano_parar = ttk.Combobox(
            aba,
            values=OPCOES_PLANOS_ENERGIA,
            state='readonly'
        )
        self.combo_plano_parar.grid(
            row=4, column=1, sticky='ew', padx=2, pady=1)
        self.combo_plano_parar.set(OPCOES_PLANOS_ENERGIA[1])  # "Equilibrado"

        # Botões de ação
        ttk.Button(aba, text="Remover", command=self._remover_monitor)\
            .grid(row=5, column=0, padx=2, pady=3, sticky='w')
        ttk.Button(aba, text="Adicionar", command=self._adicionar_monitor)\
            .grid(row=5, column=1, padx=2, pady=3, sticky='e')

        # Lista de monitores configurados
        self.lista_widget_monitores = tk.Listbox(aba, height=6)
        self.lista_widget_monitores.grid(
            row=6, column=0, columnspan=3, sticky='nsew', padx=2, pady=1)

        # Carrega monitores na lista
        self._atualizar_lista_monitores()

    def _ao_focar_campo_tecla(self, evento):
        """
        Handler chamado quando campo de tecla recebe foco.
        Remove placeholder e inicia captura de tecla.
        """
        if self.campo_tecla.get() == self.PLACEHOLDER_TECLA:
            self.campo_tecla.delete(0, tk.END)
            # Inicia captura de teclas globalmente
            self.bind_all("<KeyPress>", self._capturar_tecla_pressionada)

    def _ao_desfocar_campo_tecla(self, evento):
        """
        Handler chamado quando campo de tecla perde foco.
        Restaura placeholder se campo estiver vazio.
        """
        if not self.campo_tecla.get():
            self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)

    def _capturar_tecla_pressionada(self, evento):
        """
        Captura a tecla pressionada e insere no campo.

        Args:
            evento: Evento de tecla pressionada
        """
        # Determina representação da tecla
        if evento.char and len(evento.char) == 1:
            # Caractere imprimível
            representacao_tecla = evento.char
        else:
            # Tecla especial (ex: F1, Ctrl, etc)
            representacao_tecla = f"Key.{evento.keysym.lower()}"

        # Insere tecla no campo
        self.campo_tecla.delete(0, tk.END)
        self.campo_tecla.insert(0, representacao_tecla)

        # Para captura de teclas
        self.unbind_all("<KeyPress>")

    def _atualizar_lista_atalhos(self):
        """
        Atualiza a lista visual de atalhos configurados.
        """
        self.lista_widget_atalhos.delete(0, tk.END)
        for atalho in self.lista_atalhos:
            texto_atalho = f"{atalho['tecla']} → {atalho['comando']}"
            self.lista_widget_atalhos.insert(tk.END, texto_atalho)

    def _adicionar_atalho(self):
        """
        Adiciona novo atalho à configuração.
        """
        tecla = self.campo_tecla.get().strip()
        comando = self.campo_comando.get().strip()

        # Validação dos campos
        if not tecla or tecla.startswith("Clique") or not comando:
            messagebox.showwarning("Atenção", "Defina tecla e comando válidos")
            return

        # Adiciona atalho à lista
        novo_atalho = {"tecla": tecla, "comando": comando}
        self.lista_atalhos.append(novo_atalho)

        # Salva configurações
        self.configuracoes["atalhos"] = self.lista_atalhos
        salvar_configuracoes(self.configuracoes)

        # Limpa campos
        self.campo_tecla.delete(0, tk.END)
        self.campo_tecla.insert(0, self.PLACEHOLDER_TECLA)
        self.campo_comando.delete(0, tk.END)

        # Atualiza lista visual
        self._atualizar_lista_atalhos()

    def _remover_atalho(self):
        """
        Remove atalho selecionado da configuração.
        """
        selecao = self.lista_widget_atalhos.curselection()
        if not selecao:
            messagebox.showinfo(
                "Informação", "Selecione um atalho para remover")
            return

        # Remove atalho da lista
        indice = selecao[0]
        del self.lista_atalhos[indice]

        # Salva configurações
        self.configuracoes["atalhos"] = self.lista_atalhos
        salvar_configuracoes(self.configuracoes)

        # Atualiza lista visual
        self._atualizar_lista_atalhos()

    def _alternar_atalho_calculadora(self):
        """
        Alterna ativação do atalho especial para calculadora.
        """
        self.configuracoes["enable_calc_percent"] = self.atalho_calculadora_ativo.get(
        )
        salvar_configuracoes(self.configuracoes)

    def _procurar_arquivo(self):
        """
        Abre diálogo para selecionar arquivo executável.
        """
        caminho_arquivo = filedialog.askopenfilename(
            title="Selecione executável",
            filetypes=[("Executáveis", "*.exe"), ("Todos os arquivos", "*.*")]
        )

        if caminho_arquivo:
            # Normaliza caminho e insere no campo
            caminho_normalizado = os.path.normpath(caminho_arquivo)
            self.campo_comando.delete(0, tk.END)
            self.campo_comando.insert(0, caminho_normalizado)

    def _atualizar_lista_monitores(self):
        """
        Atualiza a lista visual de monitores de energia configurados.
        """
        self.lista_widget_monitores.delete(0, tk.END)
        for monitor in self.lista_monitores:
            # Converte prioridade interna para exibição
            prioridade_exibicao = PRIORIDADE_INTERNO_PARA_EXIBICAO.get(
                monitor['priority'],
                monitor['priority']
            )

            # Formata texto do monitor
            texto_monitor = (
                f"{monitor['process']} | {prioridade_exibicao} | "
                f"On:{monitor['power_on']} | Off:{monitor['power_off']}"
            )
            self.lista_widget_monitores.insert(tk.END, texto_monitor)

    def _adicionar_monitor(self):
        """
        Adiciona novo monitor de energia à configuração.
        """
        nome_processo = self.campo_processo.get().strip()

        if not nome_processo:
            messagebox.showwarning("Atenção", "Informe o nome do processo")
            return

        # Obtém valores dos combos
        prioridade_exibicao = self.combo_prioridade.get()
        prioridade_interna = PRIORIDADE_EXIBICAO_PARA_INTERNO[prioridade_exibicao]
        plano_iniciar = self.combo_plano_iniciar.get()
        plano_parar = self.combo_plano_parar.get()

        # Validação adicional - só permite planos suportados
        if plano_iniciar not in OPCOES_PLANOS_ENERGIA:
            messagebox.showerror("Erro", f"Plano '{plano_iniciar}' não é suportado.")
            return
        
        if plano_parar not in OPCOES_PLANOS_ENERGIA:
            messagebox.showerror("Erro", f"Plano '{plano_parar}' não é suportado.")
            return

        # Cria novo monitor
        novo_monitor = {
            "process": nome_processo,
            "priority": prioridade_interna,
            "power_on": plano_iniciar,
            "power_off": plano_parar
        }

        # Adiciona à lista
        self.lista_monitores.append(novo_monitor)

        # Salva configurações
        self.configuracoes["monitores"] = self.lista_monitores
        salvar_configuracoes(self.configuracoes)

        # Limpa campo
        self.campo_processo.delete(0, tk.END)

        # Atualiza lista visual
        self._atualizar_lista_monitores()

    def _remover_monitor(self):
        """
        Remove monitor selecionado da configuração.
        """
        selecao = self.lista_widget_monitores.curselection()
        if not selecao:
            messagebox.showinfo(
                "Informação", "Selecione um monitor para remover")
            return

        # Remove monitor da lista
        indice = selecao[0]
        del self.lista_monitores[indice]

        # Salva configurações
        self.configuracoes["monitores"] = self.lista_monitores
        salvar_configuracoes(self.configuracoes)

        # Atualiza lista visual
        self._atualizar_lista_monitores()


if __name__ == "__main__":
    # Cria e executa aplicação
    aplicacao = InterfaceConfigurador(DEFAULT_CONFIG)
    aplicacao.mainloop()