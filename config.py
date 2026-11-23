"""Caminhos, configuração padrão e leitura/gravação do config.json (com migração da v1)."""
import copy
import json
import os
import shutil
import sys

# ---------- Caminhos ----------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    RECURSOS_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RECURSOS_DIR = BASE_DIR

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
CONFIG_DIR = os.path.join(APPDATA, "TurboAtalho")
ARQUIVO_CONFIG = os.path.join(CONFIG_DIR, "config.json")
PASTA_SLOTS = os.path.join(CONFIG_DIR, "slots")

os.makedirs(PASTA_SLOTS, exist_ok=True)

# ---------- Constantes ----------
VERSAO_CONFIG = 2
TOTAL_SLOTS = 9
TEMPO_DUPLO_TOQUE = 0.45          # segundos entre dois toques
INTERVALO_MONITOR_JOGOS = 2       # segundos

GUID_EQUILIBRADO = "381b4222-f694-41f0-9685-ff5bb260df2e"

# Prioridade gravada no registro (IFEO → PerfOptions → CpuPriorityClass)
PRIORIDADES = {
    "Normal": None,            # None = remove o ajuste
    "Acima do normal": 6,
    "Alta": 3,
}


def slot_vazio():
    return {"tipo": "vazio", "texto": "", "fixo": False}


DEFAULT_CONFIG = {
    "versao": VERSAO_CONFIG,
    "calc_percent": True,
    "atalhos": [
        {"tecla": "num lock", "comando": "calc.exe"},
    ],
    "slots": [slot_vazio() for _ in range(TOTAL_SLOTS)],
    "jogos": [],
    "plano_fora": GUID_EQUILIBRADO,
}

# ---------- Migração da v1 (pynput / customtkinter) ----------
_PLANOS_V1 = {
    "Alto desempenho": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "Equilibrado": GUID_EQUILIBRADO,
    "Economia de energia": "a1841308-3541-4fab-bc81-f71556f20b4a",
}

_TECLAS_V1 = {
    "Key.ctrl_l": "ctrl", "Key.ctrl_r": "right ctrl",
    "Key.shift_l": "shift", "Key.shift_r": "right shift",
    "Key.alt_l": "alt", "Key.alt_r": "alt gr",
    "Key.cmd_l": "left windows", "Key.cmd_r": "right windows",
    "Key.cmd": "left windows", "Key.esc": "esc",
}


def _migrar_tecla(tecla):
    if tecla in _TECLAS_V1:
        return _TECLAS_V1[tecla]
    if tecla.startswith("Key."):
        return tecla[4:].replace("_", " ")
    return tecla.lower()


def _migrar_v1(antigo):
    novo = copy.deepcopy(DEFAULT_CONFIG)
    novo["calc_percent"] = antigo.get("enable_calc_percent", True)
    novo["atalhos"] = [
        {"tecla": _migrar_tecla(a.get("tecla", "")), "comando": a.get("comando", "")}
        for a in antigo.get("atalhos", []) if a.get("tecla") and a.get("comando")
    ]
    for i, texto in enumerate(antigo.get("fixed_clip_slots", [])[:TOTAL_SLOTS]):
        if texto:
            novo["slots"][i] = {"tipo": "texto", "texto": texto, "fixo": True}
    for m in antigo.get("monitores", []):
        exe = m.get("process", "").strip()
        if not exe:
            continue
        if not exe.lower().endswith(".exe"):
            exe += ".exe"
        novo["jogos"].append({
            "exe": exe,
            "prioridade": m.get("priority", "Alta"),
            "plano": _PLANOS_V1.get(m.get("power_on"), ""),
        })
    return novo


# ---------- API ----------

def obter_caminho_recurso(caminho_relativo):
    for base in (BASE_DIR, RECURSOS_DIR):
        caminho = os.path.join(base, caminho_relativo)
        if os.path.exists(caminho):
            return caminho
    return caminho_relativo


def caminho_imagem_slot(indice):
    return os.path.join(PASTA_SLOTS, f"{indice + 1}.png")


def carregar_configuracoes():
    """Lê o config.json; cria o padrão se não existir e migra a v1 se precisar."""
    if not os.path.exists(ARQUIVO_CONFIG):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        salvar_configuracoes(cfg)
        return cfg
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(DEFAULT_CONFIG)

    if cfg.get("versao") != VERSAO_CONFIG:
        shutil.copy2(ARQUIVO_CONFIG, os.path.join(CONFIG_DIR, "config.v1.json"))
        cfg = _migrar_v1(cfg)
        salvar_configuracoes(cfg)

    for chave, valor in DEFAULT_CONFIG.items():
        cfg.setdefault(chave, copy.deepcopy(valor))
    slots = cfg["slots"][:TOTAL_SLOTS]
    slots += [slot_vazio() for _ in range(TOTAL_SLOTS - len(slots))]
    cfg["slots"] = slots
    return cfg


def salvar_configuracoes(cfg):
    temporario = ARQUIVO_CONFIG + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(temporario, ARQUIVO_CONFIG)
