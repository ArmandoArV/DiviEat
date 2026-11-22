"""Medicion de la extraccion, de punta a punta.

El CER de una linea no dice si el ticket sirve: lo que importa es si salieron
los productos correctos, si el total se leyo bien y si el cuadre acaba en
verde. Este modulo mide eso sobre los tickets sinteticos, donde la verdad de
referencia es exacta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from divieat_ticket.dominio import Producto, TicketExtraido
from divieat_ticket.modelo.metricas import TasaDeError
from divieat_ticket.pipeline import PipelineExtraccionTicket
from divieat_ticket.sintetico import GeneradorTicketsSinteticos, MuestraSintetica


@dataclass(frozen=True)
class ComparacionDeTicket:
    """Resultado de comparar un ticket extraido contra su verdad."""

    aciertos: int
    predichos: int
    esperados: int
    total_correcto: bool
    cuadre_correcto: bool
    error_suma_centavos: int

    @property
    def precision(self) -> float:
        return self.aciertos / self.predichos if self.predichos else 0.0

    @property
    def exhaustividad(self) -> float:
        return self.aciertos / self.esperados if self.esperados else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.exhaustividad
        return 2 * p * r / (p + r) if (p + r) else 0.0


class ComparadorDeProductos:
    """Empareja productos predichos con los verdaderos.

    Un producto cuenta como acierto si el importe coincide al centavo y la
    descripcion se parece lo suficiente: el OCR puede equivocarse en una letra
    sin que el comensal deje de reconocer su platillo.
    """

    def __init__(self, umbral_similitud: float = 0.75) -> None:
        self.umbral_similitud = umbral_similitud

    def emparejar(self, predichos: list[Producto], esperados: list[Producto]) -> int:
        disponibles = list(esperados)
        aciertos = 0
        for predicho in predichos:
            mejor, mejor_puntaje = None, 0.0
            for candidato in disponibles:
                if candidato.importe != predicho.importe:
                    continue
                puntaje = self._similitud(predicho.descripcion, candidato.descripcion)
                if puntaje > mejor_puntaje:
                    mejor, mejor_puntaje = candidato, puntaje
            if mejor is not None and mejor_puntaje >= self.umbral_similitud:
                disponibles.remove(mejor)
                aciertos += 1
        return aciertos

    @staticmethod
    def _similitud(a: str, b: str) -> float:
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()


@dataclass
class ResumenEvaluacion:
    """Agregado sobre un conjunto de tickets."""

    comparaciones: list[ComparacionDeTicket] = field(default_factory=list)
    motor: str = ""
    cer_lineas: float | None = None

    def agregar(self, comparacion: ComparacionDeTicket) -> None:
        self.comparaciones.append(comparacion)

    @property
    def tickets(self) -> int:
        return len(self.comparaciones)

    def _media(self, atributo: str) -> float:
        if not self.comparaciones:
            return 0.0
        return sum(getattr(c, atributo) for c in self.comparaciones) / len(self.comparaciones)

    @property
    def precision(self) -> float:
        return self._media("precision")

    @property
    def exhaustividad(self) -> float:
        return self._media("exhaustividad")

    @property
    def f1(self) -> float:
        return self._media("f1")

    @property
    def tasa_total_correcto(self) -> float:
        if not self.comparaciones:
            return 0.0
        return sum(c.total_correcto for c in self.comparaciones) / len(self.comparaciones)

    @property
    def tasa_cuadre(self) -> float:
        if not self.comparaciones:
            return 0.0
        return sum(c.cuadre_correcto for c in self.comparaciones) / len(self.comparaciones)

    def __str__(self) -> str:
        cer = f"{self.cer_lineas:.4f}" if self.cer_lineas is not None else "n/d"
        return (
            f"{self.motor:<16} tickets {self.tickets:>3} · CER {cer} · "
            f"P {self.precision:.3f} · R {self.exhaustividad:.3f} · F1 {self.f1:.3f} · "
            f"total ok {self.tasa_total_correcto:.3f} · cuadre ok {self.tasa_cuadre:.3f}"
        )


class EvaluadorDeExtraccion:
    """Corre un pipeline sobre tickets sinteticos y resume su desempeno."""

    def __init__(self, comparador: ComparadorDeProductos | None = None) -> None:
        self.comparador = comparador or ComparadorDeProductos()
        self.metrica_cer = TasaDeError()

    def comparar(self, predicho: TicketExtraido, esperado: TicketExtraido) -> ComparacionDeTicket:
        aciertos = self.comparador.emparejar(predicho.productos, esperado.productos)
        total_esperado = esperado.total_impreso or esperado.subtotal
        total_correcto = (
            predicho.total_impreso is not None
            and total_esperado is not None
            and predicho.total_impreso == total_esperado
        )
        error = (predicho.suma_productos - esperado.suma_productos).centavos
        return ComparacionDeTicket(
            aciertos=aciertos,
            predichos=len(predicho.productos),
            esperados=len(esperado.productos),
            total_correcto=total_correcto,
            cuadre_correcto=predicho.cuadra() and esperado.cuadra(),
            error_suma_centavos=error,
        )

    def evaluar(
        self,
        pipeline: PipelineExtraccionTicket,
        muestras: list[MuestraSintetica],
    ) -> ResumenEvaluacion:
        resumen = ResumenEvaluacion(motor=pipeline.motor.nombre)
        for muestra in muestras:
            extraido = pipeline.procesar(muestra.imagen)
            resumen.agregar(self.comparar(extraido, muestra.verdad))
        return resumen

    @staticmethod
    def muestras(cantidad: int, semilla: int = 99) -> list[MuestraSintetica]:
        from divieat_ticket.sintetico import ConfiguracionSintetico

        generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=semilla))
        return generador.lote(cantidad)
