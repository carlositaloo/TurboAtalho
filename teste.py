# teste_guids.py - Para debugar os planos de energia

import subprocess
import re

def obter_guids_planos_energia_debug():
    """
    Versão debug para ver exatamente o que está sendo retornado
    """
    try:
        resultado = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, text=True, check=True
        )
        
        print("=== OUTPUT COMPLETO DO POWERCFG ===")
        print(resultado.stdout)
        print("=== FIM OUTPUT ===\n")
        
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar powercfg: {e}")
        return {}

    mapeamento_planos = {}
    linhas_processadas = []
    
    for linha in resultado.stdout.splitlines():
        # NOVO PADRÃO: GUID do Esquema de Energia: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  (Nome do Plano)
        match = re.search(r"GUID do Esquema de Energia:\s*([0-9A-Fa-f-]+)\s*\((.+?)\)", linha)
        if match:
            guid = match.group(1).lower()
            nome = match.group(2).strip()
            # Remove o asterisco (*) se presente (indica plano ativo)
            nome = nome.rstrip(' *')
            mapeamento_planos[nome] = guid
            linhas_processadas.append(f"✓ {nome} -> {guid}")
        else:
            # Vamos ver as linhas que não deram match
            if "guid" in linha.lower() or "(" in linha:
                linhas_processadas.append(f"✗ Não deu match: {linha.strip()}")

    print("=== LINHAS PROCESSADAS ===")
    for linha in linhas_processadas:
        print(linha)
    
    print(f"\n=== RESULTADO FINAL ===")
    print(f"Total de planos encontrados: {len(mapeamento_planos)}")
    for nome, guid in mapeamento_planos.items():
        print(f"  {nome} -> {guid}")

    return mapeamento_planos

if __name__ == "__main__":
    planos = obter_guids_planos_energia_debug()