import os
import time
import subprocess

import psutil

from config import (
    carregar_configuracoes, ARQUIVO_CONFIG,
    PLANOS_ENERGIA_FIXOS,
    INTERVALO_MONITORAMENTO,
)

MAPA_PRIORIDADES = {
    "Normal":          psutil.NORMAL_PRIORITY_CLASS,
    "Acima do normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "Alta":            psutil.HIGH_PRIORITY_CLASS,
}


class GerenciadorPlanoEnergia:
    """Define o plano de energia do Windows de acordo com os processos ativos."""

    PRIORIDADE_PLANOS = {
        "Alto desempenho": 3,
        "Equilibrado": 2,
        "Economia de energia": 1,
    }

    def __init__(self):
        self.plano_atual = None
        self.processos_ativos = {}

    def adicionar_processo_ativo(self, nome, config):
        self.processos_ativos[nome] = config
        self._aplicar_plano_necessario()

    def remover_processo_ativo(self, nome):
        self.processos_ativos.pop(nome, None)
        self._aplicar_plano_necessario()

    def _obter_plano_maior_prioridade(self):
        if not self.processos_ativos:
            return "Equilibrado"
        maior = 0
        plano = "Equilibrado"
        for cfg in self.processos_ativos.values():
            p = self.PRIORIDADE_PLANOS.get(cfg['power_on'], 0)
            if p > maior:
                maior = p
                plano = cfg['power_on']
        return plano

    def _aplicar_plano_necessario(self):
        plano = self._obter_plano_maior_prioridade()
        if self.plano_atual != plano:
            if self._definir_plano_energia(plano):
                self.plano_atual = plano

    @staticmethod
    def _definir_plano_energia(nome_plano):
        guid = PLANOS_ENERGIA_FIXOS.get(nome_plano)
        if not guid:
            return False
        try:
            subprocess.run(
                ["powercfg", "-setactive", guid],
                check=True, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        except subprocess.CalledProcessError:
            return False


class GerenciadorEnergia:
    """Monitora processos e ajusta prioridade + plano de energia."""

    def __init__(self):
        cfg = carregar_configuracoes()
        self.processos_monitorados = cfg["monitores"]
        self._ts_config = os.path.getmtime(ARQUIVO_CONFIG)
        self.gerenciador_plano = GerenciadorPlanoEnergia()
        self.estado_processos = {}

        # Estado inicial
        for proc_cfg in self.processos_monitorados:
            nome = proc_cfg['process'].lower()
            ativos = [
                p for p in psutil.process_iter(['name'])
                if p.info['name'] and p.info['name'].lower().startswith(nome)
            ]
            self.estado_processos[nome] = bool(ativos)
            if ativos:
                self.gerenciador_plano.adicionar_processo_ativo(nome, proc_cfg)
                for p in ativos:
                    try:
                        pri = MAPA_PRIORIDADES.get(
                            proc_cfg['priority'], psutil.NORMAL_PRIORITY_CLASS
                        )
                        p.nice(pri)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

    def recarregar_se_necessario(self):
        try:
            ts = os.path.getmtime(ARQUIVO_CONFIG)
            if ts != self._ts_config:
                cfg = carregar_configuracoes()
                self.processos_monitorados = cfg["monitores"]
                self._ts_config = ts

                antigo = self.estado_processos.copy()
                self.estado_processos = {
                    pc['process'].lower(): False
                    for pc in self.processos_monitorados
                }
                self.gerenciador_plano.processos_ativos.clear()

                for pc in self.processos_monitorados:
                    nome = pc['process'].lower()
                    if antigo.get(nome, False):
                        encontrados = [
                            p for p in psutil.process_iter(['name'])
                            if p.info['name'] and p.info['name'].lower().startswith(nome)
                        ]
                        if encontrados:
                            self.estado_processos[nome] = True
                            self.gerenciador_plano.adicionar_processo_ativo(nome, pc)
                            for p in encontrados:
                                try:
                                    pri = MAPA_PRIORIDADES.get(
                                        pc['priority'], psutil.NORMAL_PRIORITY_CLASS
                                    )
                                    p.nice(pri)
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
        except OSError:
            pass

    def monitorar_processos(self):
        while True:
            try:
                self.recarregar_se_necessario()

                for pc in self.processos_monitorados:
                    nome = pc['process'].lower()
                    encontrados = [
                        p for p in psutil.process_iter(['name'])
                        if p.info['name'] and p.info['name'].lower().startswith(nome)
                    ]
                    ativo = bool(encontrados)

                    if ativo and not self.estado_processos.get(nome, False):
                        self.gerenciador_plano.adicionar_processo_ativo(nome, pc)
                        for p in encontrados:
                            try:
                                pri = MAPA_PRIORIDADES.get(
                                    pc['priority'], psutil.NORMAL_PRIORITY_CLASS
                                )
                                p.nice(pri)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                        self.estado_processos[nome] = True

                    elif not ativo and self.estado_processos.get(nome, False):
                        self.gerenciador_plano.remover_processo_ativo(nome)
                        self.estado_processos[nome] = False
            except Exception:
                pass

            time.sleep(INTERVALO_MONITORAMENTO)
