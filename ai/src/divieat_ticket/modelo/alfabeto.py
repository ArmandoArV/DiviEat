"""Alfabeto y codificacion para CTC.

CTC necesita una clase extra, el *blanco*, que representa «aqui no emito nada».
Se reserva el indice 0 y por eso `len(alfabeto)` es len(caracteres) + 1.
"""

from __future__ import annotations


class Alfabeto:
    """Mapea caracteres a indices y de vuelta."""

    BLANCO = 0

    # Lo que de verdad aparece en un ticket mexicano, incluido el acento y la enie.
    CARACTERES_TICKET = (
        " ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ"
        "abcdefghijklmnopqrstuvwxyzáéíóúñ"
        "0123456789"
        ".,:;/$%&@#*-+()[]='\"!?°"
    )

    def __init__(self, caracteres: str) -> None:
        vistos: list[str] = []
        for caracter in caracteres:
            if caracter not in vistos:
                vistos.append(caracter)
        self.caracteres = "".join(vistos)
        self._a_indice = {c: i + 1 for i, c in enumerate(self.caracteres)}
        self._a_caracter = {i + 1: c for i, c in enumerate(self.caracteres)}

    @classmethod
    def de_tickets(cls) -> "Alfabeto":
        return cls(cls.CARACTERES_TICKET)

    def __len__(self) -> int:
        """Numero de clases de la capa de salida (incluye el blanco)."""
        return len(self.caracteres) + 1

    def __contains__(self, caracter: str) -> bool:
        return caracter in self._a_indice

    def codificar(self, texto: str) -> list[int]:
        """Texto -> indices. Los caracteres desconocidos se descartan."""
        return [self._a_indice[c] for c in texto if c in self._a_indice]

    def decodificar(self, indices: list[int]) -> str:
        """Indices -> texto, ignorando el blanco."""
        return "".join(self._a_caracter.get(i, "") for i in indices if i != self.BLANCO)

    def limpiar(self, texto: str) -> str:
        """Deja solo lo representable, para no entrenar contra objetivos imposibles."""
        return "".join(c for c in texto if c in self._a_indice)

    def __repr__(self) -> str:
        return f"<Alfabeto {len(self)} clases (blanco + {len(self.caracteres)} caracteres)>"
