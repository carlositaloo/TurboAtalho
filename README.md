# Turbo Atalho

Utilitário Windows que roda na bandeja do sistema oferecendo três funcionalidades:
atalhos de teclado personalizados, gerenciamento de clipes e controle automático de plano de energia.

## Funcionalidades

### Atalhos de Teclado
- Mapeie qualquer tecla (incluindo teclas especiais como NumLock, Menu, F1–F12) para abrir programas ou executar comandos com duplo toque
- Atalho especial: substitui automaticamente `Shift Direito` por `%` dentro da Calculadora do Windows

### Gerenciador de Clipes
- Histórico automático dos últimos 9 itens copiados (`Ctrl+0` para visualizar)
- Colagem rápida por slot: `Ctrl+Shift+1` a `Ctrl+Shift+9`
- Mensagens fixas configuráveis por slot (independentes do histórico)

### Gerenciador de Energia
- Monitora processos em segundo plano e altera automaticamente o plano de energia do Windows quando um processo configurado inicia ou para
- Define a prioridade de CPU do processo monitorado (Normal / Acima do normal / Alta)

## Tecnologias
- Python 3.13+
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — interface gráfica
- [pynput](https://pynput.readthedocs.io/) — captura de teclado global
- [keyboard](https://github.com/boppreh/keyboard) — atalhos globais de colagem
- [pystray](https://github.com/moses-palmer/pystray) — ícone na bandeja do sistema
- [psutil](https://github.com/giampaolo/psutil) — monitoramento de processos
- [pyperclip](https://github.com/asweigart/pyperclip) — acesso à área de transferência

## Instalação e Uso

### Rodando pelo código-fonte
Requer [uv](https://docs.astral.sh/uv/).
```bash
uv sync
uv run main.py
```

### Gerando o executável
```bash
build.bat
```
O executável será gerado em `dist\TurboAtalho.exe`. Requer execução como administrador (necessário para alterar prioridade de processos e plano de energia).

## Configurações
As configurações ficam salvas em `%APPDATA%\TurboAtalho\config.json` e são editadas pela janela de opções acessível pelo ícone na bandeja.
