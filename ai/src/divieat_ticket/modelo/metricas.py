"""Metricas de reconocimiento."""

from __future__ import annotations

from dataclasses import dataclass


def distancia_de_edicion(a: str, b: str) -> int:
    """Levenshtein con una sola fila de memoria."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    fila = list(range(len(b) + 1))
    for i, caracter_a in enumerate(a, start=1):
        anterior, fila[0] = fila[0], i
        for j, caracter_b in enumerate(b, start=1):
            actual = fila[j]
            fila[j] = min(
                fila[j] + 1,                                   # borrar
                fila[j - 1] + 1,                               # insertar
                anterior + (caracter_a != caracter_b),         # sustituir
            )
            anterior = actual
    return fila[-1]


@dataclass(frozen=True)
class ResultadoMetrica:
    errores: int
    referencia: int

    @property
    def tasa(self) -> float:
        return self.errores / self.referencia if self.referencia else 0.0

    def __str__(self) -> str:
        return f"{self.tasa:.4f} ({self.errores}/{self.referencia})"


class TasaDeError:
    """CER o WER segun la unidad: caracteres o palabras."""

    def __init__(self, por_palabra: bool = False) -> None:
        self.por_palabra = por_palabra

    @property
    def nombre(self) -> str:
        return "WER" if self.por_palabra else "CER"

    def medir(self, predichos: list[str], verdaderos: list[str]) -> ResultadoMetrica:
        if len(predichos) != len(verdaderos):
            raise ValueError("las listas deben tener el mismo largo")
        errores = total = 0
        for predicho, verdadero in zip(predichos, verdaderos):
            if self.por_palabra:
                p, v = predicho.split(), verdadero.split()
                errores += distancia_de_edicion(" ".join(p), " ".join(v)) if False else _wer(p, v)
                total += len(v)
            else:
                errores += distancia_de_edicion(predicho, verdadero)
                total += len(verdadero)
        return ResultadoMetrica(errores, total)


def _wer(predicho: list[str], verdadero: list[str]) -> int:
    """Levenshtein a nivel de palabra."""
    if predicho == verdadero:
        return 0
    fila = list(range(len(verdadero) + 1))
    for i, palabra_p in enumerate(predicho, start=1):
        anterior, fila[0] = fila[0], i
        for j, palabra_v in enumerate(verdadero, start=1):
            actual = fila[j]
            fila[j] = min(fila[j] + 1, fila[j - 1] + 1, anterior + (palabra_p != palabra_v))
            anterior = actual
    return fila[-1]
