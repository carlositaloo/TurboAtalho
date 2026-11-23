"""Funções do Windows: janela ativa, planos de energia, prioridade no registro, iniciar com o Windows."""
import ctypes
import ctypes.wintypes as wt
import os
import re
import subprocess
import sys
import winreg

_SEM_JANELA = subprocess.CREATE_NO_WINDOW
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_shell32 = ctypes.WinDLL("shell32", use_last_error=True)


# ---------- Janelas ----------

def janela_ativa():
    return _user32.GetForegroundWindow()


def titulo_janela_ativa():
    hwnd = _user32.GetForegroundWindow()
    tamanho = _user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(tamanho + 1)
    _user32.GetWindowTextW(hwnd, buf, tamanho + 1)
    return buf.value


def focar_janela(hwnd):
    if hwnd:
        _user32.SetForegroundWindow(hwnd)


# ---------- Abrir programas ----------

def abrir_comando(comando):
    """Abre um programa, arquivo ou comando (ex.: calc.exe, C:\\...\\app.exe, 'notepad arquivo.txt')."""
    try:
        os.startfile(comando)
    except OSError:
        subprocess.Popen(f'start "" {comando}', shell=True, creationflags=_SEM_JANELA)


# ---------- Planos de energia ----------

def listar_planos():
    """Retorna [(guid, nome, ativo)] lidos do `powercfg /list`."""
    try:
        saida = subprocess.run(
            ["powercfg", "/list"], capture_output=True, creationflags=_SEM_JANELA,
        ).stdout.decode("oem", errors="replace")
    except OSError:
        return []
    padrao = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s+\((.+?)\)(\s*\*)?", re.I)
    return [(g.lower(), nome, bool(ativo)) for g, nome, ativo in padrao.findall(saida)]


def definir_plano(guid):
    if not guid:
        return False
    r = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, creationflags=_SEM_JANELA)
    return r.returncode == 0


# ---------- Prioridade fixa por .exe (registro) ----------

_IFEO = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"


def ler_prioridade(exe):
    """Valor de CpuPriorityClass gravado para o .exe, ou None."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"{_IFEO}\{exe}\PerfOptions",
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return winreg.QueryValueEx(k, "CpuPriorityClass")[0]
    except OSError:
        return None


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wt.HWND),
        ("lpVerb", wt.LPCWSTR), ("lpFile", wt.LPCWSTR), ("lpParameters", wt.LPCWSTR),
        ("lpDirectory", wt.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wt.HINSTANCE),
        ("lpIDList", ctypes.c_void_p), ("lpClass", wt.LPCWSTR), ("hkeyClass", wt.HKEY),
        ("dwHotKey", wt.DWORD), ("hIconOrMonitor", wt.HANDLE), ("hProcess", wt.HANDLE),
    ]


def _executar_como_admin(arquivo, parametros):
    """Roda um programa pedindo UAC e espera terminar. Retorna True se saiu com código 0."""
    info = _SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = arquivo
    info.lpParameters = parametros
    info.nShow = 0
    if not _shell32.ShellExecuteExW(ctypes.byref(info)) or not info.hProcess:
        return False  # usuário recusou o UAC
    _kernel32.WaitForSingleObject(info.hProcess, 30000)
    codigo = wt.DWORD()
    _kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(codigo))
    _kernel32.CloseHandle(info.hProcess)
    return codigo.value == 0


def gravar_prioridade(exe, valor):
    """Grava (valor int) ou remove (valor None) a prioridade fixa do .exe. Pede UAC se precisar."""
    chave = rf"HKLM\{_IFEO}\{exe}\PerfOptions"
    if valor is None:
        if ler_prioridade(exe) is None:
            return True
        parametros = f'delete "{chave}" /f'
    else:
        parametros = f'add "{chave}" /v CpuPriorityClass /t REG_DWORD /d {int(valor)} /f'
    return _executar_como_admin("reg.exe", parametros)


# ---------- Iniciar com o Windows ----------

_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NOME_RUN = "TurboAtalho"


def _comando_inicializacao():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{pythonw}" "{main}"'


def inicia_com_windows():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN) as k:
            winreg.QueryValueEx(k, _NOME_RUN)
            return True
    except OSError:
        return False


def definir_inicio_com_windows(ativo):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN, 0, winreg.KEY_SET_VALUE) as k:
        if ativo:
            winreg.SetValueEx(k, _NOME_RUN, 0, winreg.REG_SZ, _comando_inicializacao())
        else:
            try:
                winreg.DeleteValue(k, _NOME_RUN)
            except FileNotFoundError:
                pass
