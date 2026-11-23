"""Os 9 slots de colagem: guardam texto ou imagem, ficam salvos no disco e podem ser fixados."""
import os
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication, QImage

from config import TOTAL_SLOTS, caminho_imagem_slot, salvar_configuracoes, slot_vazio


class Slots(QObject):
    mudou = Signal()

    def __init__(self, cfg):
        super().__init__()
        self._cfg = cfg
        self._imagens = {}
        for i, s in enumerate(self.itens):
            if s["tipo"] == "imagem":
                img = QImage(caminho_imagem_slot(i))
                if img.isNull():
                    self.itens[i] = slot_vazio()
                else:
                    self._imagens[i] = img

    @property
    def itens(self):
        return self._cfg["slots"]

    def imagem(self, i):
        return self._imagens.get(i)

    # ---------- guardar ----------

    def _proximo_indice(self):
        livres = [i for i, s in enumerate(self.itens) if s["tipo"] == "vazio"]
        if livres:
            return livres[0]
        trocaveis = [i for i, s in enumerate(self.itens) if not s["fixo"]]
        if not trocaveis:
            return None
        return min(trocaveis, key=lambda i: self.itens[i].get("quando", 0))

    def guardar_da_area(self):
        """Lê a área de transferência e guarda no próximo slot. Retorna o índice ou None."""
        dados = QGuiApplication.clipboard().mimeData()
        if dados is None:
            return None
        if dados.hasImage():
            img = QImage(dados.imageData())
            if img.isNull():
                return None
            i = self._proximo_indice()
            if i is None:
                return None
            self._definir_imagem(i, img)
            return i
        texto = dados.text() if dados.hasText() else ""
        if not texto.strip():
            return None
        i = self._proximo_indice()
        if i is None:
            return None
        self._definir_texto(i, texto)
        return i

    def _definir_texto(self, i, texto, fixo=None):
        self._remover_imagem(i)
        anterior = self.itens[i]
        self.itens[i] = {
            "tipo": "texto", "texto": texto, "quando": time.time(),
            "fixo": anterior["fixo"] if fixo is None else fixo,
        }
        self._salvar()

    def _definir_imagem(self, i, img):
        img.save(caminho_imagem_slot(i), "PNG")
        self._imagens[i] = img
        anterior = self.itens[i]
        self.itens[i] = {"tipo": "imagem", "texto": "", "quando": time.time(), "fixo": anterior["fixo"]}
        self._salvar()

    def editar_texto(self, i, texto):
        if texto.strip():
            self._definir_texto(i, texto)
        else:
            self.limpar(i)

    # ---------- colar ----------

    def copiar_para_area(self, i):
        """Coloca o slot na área de transferência. Retorna False se estiver vazio."""
        s = self.itens[i]
        area = QGuiApplication.clipboard()
        if s["tipo"] == "texto":
            area.setText(s["texto"])
            return True
        if s["tipo"] == "imagem" and i in self._imagens:
            area.setImage(self._imagens[i])
            return True
        return False

    # ---------- organizar ----------

    def alternar_fixo(self, i):
        self.itens[i]["fixo"] = not self.itens[i]["fixo"]
        self._salvar()

    def limpar(self, i):
        self._remover_imagem(i)
        self.itens[i] = slot_vazio()
        self._salvar()

    def limpar_nao_fixados(self):
        for i in range(TOTAL_SLOTS):
            if not self.itens[i]["fixo"]:
                self._remover_imagem(i)
                self.itens[i] = slot_vazio()
        self._salvar()

    def _remover_imagem(self, i):
        self._imagens.pop(i, None)
        try:
            os.remove(caminho_imagem_slot(i))
        except FileNotFoundError:
            pass

    def _salvar(self):
        salvar_configuracoes(self._cfg)
        self.mudou.emit()
