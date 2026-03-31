import json
import os
import sys
import subprocess

# ---------- Paths ----------
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    SCRIPT_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_DIR = BASE_DIR

APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
CONFIG_DIR = os.path.join(APPDATA, 'TurboAtalho')
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, 'config.json')

os.makedirs(CONFIG_DIR, exist_ok=True)

# ---------- Constantes ----------
INTERVALO_MONITORAMENTO = 2
TEMPO_DUPLO_CLIQUE = 0.5

FLAG_NOVA_JANELA = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0

OPCOES_PRIORIDADE = ["Normal", "Acima do normal", "Alta"]

OPCOES_PLANOS_ENERGIA = [
    "Alto desempenho",
    "Equilibrado",
    "Economia de energia",
]

PLANOS_ENERGIA_FIXOS = {
    "Alto desempenho":     "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "Equilibrado":         "381b4222-f694-41f0-9685-ff5bb260df2e",
    "Economia de energia": "a1841308-3541-4fab-bc81-f71556f20b4a",
}

DEFAULT_CONFIG = {
    "enable_calc_percent": True,
    "enable_clip_history": True,
    "enable_clip_paste": True,
    "fixed_clip_slots": ["" for _ in range(9)],
    "atalhos": [
        {"tecla": "Key.num_lock", "comando": "calc.exe"},
        {"tecla": "Key.menu",     "comando": "notepad.exe"},
        {"tecla": "Key.home",     "comando": "powershell.exe"},
    ],
    "monitores": [],
}

# ---------- Helpers ----------

def obter_caminho_recurso(caminho_relativo):
    """Caminho correto para recursos empacotados ou em dev."""
    caminho_base = os.path.join(BASE_DIR, caminho_relativo)
    if os.path.exists(caminho_base):
        return caminho_base
    caminho_temp = os.path.join(SCRIPT_DIR, caminho_relativo)
    if os.path.exists(caminho_temp):
        return caminho_temp
    return caminho_relativo


def carregar_configuracoes():
    """Carrega config.json; cria com DEFAULT_CONFIG se não existir."""
    if not os.path.exists(ARQUIVO_CONFIG):
        salvar_configuracoes(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        # Garantir que chaves novas existam
        for chave, valor in DEFAULT_CONFIG.items():
            cfg.setdefault(chave, valor)
        return cfg
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_CONFIG.copy()


def salvar_configuracoes(configuracoes):
    """Salva configuracoes em config.json."""
    with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(configuracoes, f, indent=4, ensure_ascii=False)
