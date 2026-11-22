"""Decodificacion CTC.

La red emite una distribucion por columna; CTC permite que varias columnas
produzcan el mismo caracter y que otras emitan «blanco». Para leer el texto
hay que colapsar repeticiones y luego quitar los blancos. Ese orden importa:
al reves, «ll» de «GALLO» se perderia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import torch

from divieat_ticket.modelo.alfabeto import Alfabeto


class DecodificadorCTC(ABC):
    """Convierte (T,B,clases) en textos."""

    def __init__(self, alfabeto: Alfabeto) -> None:
        self.alfabeto = alfabeto

    @abstractmethod
    def decodificar(self, log_probabilidades: torch.Tensor) -> list[str]:
        ...

    @property
    def nombre(self) -> str:
        return type(self).__name__


class DecodificadorVoraz(DecodificadorCTC):
    """Mejor camino: toma el argmax por columna. Rapido y suficiente aqui."""

    def decodificar(self, log_probabilidades: torch.Tensor) -> list[str]:
        mejores = log_probabilidades.argmax(dim=2)       # (T, B)
        textos = []
        for columna in mejores.permute(1, 0).tolist():   # por muestra
            textos.append(self.alfabeto.decodificar(self._colapsar(columna)))
        return textos

    def confianza(self, log_probabilidades: torch.Tensor) -> list[float]:
        """Probabilidad media del camino elegido, como proxy de confianza."""
        probabilidades = log_probabilidades.exp()
        maximos = probabilidades.max(dim=2).values       # (T, B)
        return maximos.mean(dim=0).tolist()

    @staticmethod
    def _colapsar(indices: list[int]) -> list[int]:
        """Colapsa repeticiones y despues elimina los blancos."""
        colapsado: list[int] = []
        anterior = None
        for indice in indices:
            if indice != anterior:
                colapsado.append(indice)
            anterior = indice
        return [i for i in colapsado if i != Alfabeto.BLANCO]
