"""Etiquetado de recortes a partir de fotos reales.

La CRNN entrenada solo con sinteticos no transfiere: lee 3/9 productos en una
foto de verdad. Lo que falta son recortes reales etiquetados, y hay pocas
fotos, asi que no se puede desperdiciar ninguna.

Exigir que el segmentador encuentre exactamente tantos renglones como tiene la
transcripcion descarta casi todo (en sinteticos ese criterio ya solo acepta el
46%). Aqui se usa otra via: un OCR que **si** funciona sobre fotos reales lee
cada recorte de forma aproximada, y esa secuencia ruidosa se **alinea** contra
la transcripcion exacta. Donde la alineacion es confiable, la transcripcion es
la etiqueta; donde no, el recorte se descarta.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Sequence

import cv2

from divieat_ticket.imagen import Imagen
from divieat_ticket.modelo.corpus import normalizar_recorte
from divieat_ticket.ocr import CajaTexto, MotorOCR, Segmentador


@dataclass(frozen=True)
class Emparejamiento:
    """Un recorte con la etiqueta que se le asigno y cuanto se confia en ella."""

    indice_recorte: int
    texto_verdadero: str
    texto_leido: str
    similitud: float


class AlineadorDeSecuencias:
    """Alinea dos listas de renglones conservando el orden (Needleman-Wunsch).

    No se emparejan renglones por separado a proposito: un ticket repite
    descripciones («COCA COLA» dos veces) y el mejor emparejamiento aislado se
    equivocaria. El orden es informacion y hay que usarla.
    """

    def __init__(self, penalizacion_hueco: float = 0.45, umbral: float = 0.55) -> None:
        self.penalizacion_hueco = penalizacion_hueco
        self.umbral = umbral

    @staticmethod
    def similitud(a: str, b: str) -> float:
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()

    def alinear(self, leidos: Sequence[str], verdaderos: Sequence[str]) -> list[Emparejamiento]:
        n, m = len(leidos), len(verdaderos)
        if not n or not m:
            return []

        puntajes = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            puntajes[i][0] = puntajes[i - 1][0] - self.penalizacion_hueco
        for j in range(1, m + 1):
            puntajes[0][j] = puntajes[0][j - 1] - self.penalizacion_hueco

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                diagonal = puntajes[i - 1][j - 1] + self.similitud(leidos[i - 1], verdaderos[j - 1])
                puntajes[i][j] = max(
                    diagonal,
                    puntajes[i - 1][j] - self.penalizacion_hueco,
                    puntajes[i][j - 1] - self.penalizacion_hueco,
                )

        emparejamientos: list[Emparejamiento] = []
        i, j = n, m
        while i > 0 and j > 0:
            diagonal = puntajes[i - 1][j - 1] + self.similitud(leidos[i - 1], verdaderos[j - 1])
            if abs(puntajes[i][j] - diagonal) < 1e-9:
                similitud = self.similitud(leidos[i - 1], verdaderos[j - 1])
                if similitud >= self.umbral:
                    emparejamientos.append(
                        Emparejamiento(i - 1, verdaderos[j - 1], leidos[i - 1], similitud)
                    )
                i, j = i - 1, j - 1
            elif abs(puntajes[i][j] - (puntajes[i - 1][j] - self.penalizacion_hueco)) < 1e-9:
                i -= 1
            else:
                j -= 1
        return sorted(emparejamientos, key=lambda e: e.indice_recorte)


@dataclass
class EstadisticasReales:
    fotos: int = 0
    recortes: int = 0
    etiquetados: int = 0
    por_foto: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def rendimiento(self) -> float:
        return self.etiquetados / self.recortes if self.recortes else 0.0

    def __str__(self) -> str:
        return (f"{self.etiquetados} recortes etiquetados de {self.recortes} "
                f"en {self.fotos} fotos (rendimiento {self.rendimiento:.0%})")


class EtiquetadorDeRecortesReales:
    """Convierte fotos + transcripcion en pares (recorte, texto) de entrenamiento."""

    def __init__(
        self,
        carpeta: str | Path,
        cadena,
        segmentador: Segmentador,
        motor: MotorOCR,
        alineador: AlineadorDeSecuencias | None = None,
    ) -> None:
        self.carpeta = Path(carpeta)
        self.cadena = cadena
        self.segmentador = segmentador
        self.motor = motor
        self.alineador = alineador or AlineadorDeSecuencias()
        self.estadisticas = EstadisticasReales()

    def etiquetar(self, fotos: Sequence[tuple[str, Path, Sequence[str]]]) -> EstadisticasReales:
        """`fotos` es [(nombre, ruta, renglones transcritos)]."""
        self.carpeta.mkdir(parents=True, exist_ok=True)
        with (self.carpeta / "etiquetas.jsonl").open("w", encoding="utf-8") as archivo:
            for nombre, ruta, verdaderos in fotos:
                emparejados, total = self._una_foto(nombre, ruta, verdaderos, archivo)
                self.estadisticas.fotos += 1
                self.estadisticas.recortes += total
                self.estadisticas.etiquetados += emparejados
                self.estadisticas.por_foto[nombre] = (emparejados, total)
                print(f"  {nombre:<14} {emparejados:>3}/{total:>3} recortes etiquetados",
                      flush=True)
        return self.estadisticas

    def _una_foto(self, nombre: str, ruta: Path, verdaderos: Sequence[str], archivo) -> tuple[int, int]:
        procesada = self.cadena.aplicar(Imagen.desde_archivo(ruta))
        cajas = self.segmentador.segmentar(procesada)
        if not cajas:
            return 0, 0

        leidos = self._leer_recortes(procesada, cajas)
        utiles = [t for t in verdaderos if t.strip() and set(t.strip()) - set("-=_~.*")]
        emparejamientos = self.alineador.alinear(leidos, utiles)

        for emparejamiento in emparejamientos:
            caja = cajas[emparejamiento.indice_recorte]
            recorte = normalizar_recorte(caja.recortar(procesada).a_gris().matriz)
            archivo_imagen = f"{nombre}_{emparejamiento.indice_recorte:03d}.png"
            cv2.imwrite(str(self.carpeta / archivo_imagen), recorte)
            archivo.write(json.dumps({
                "imagen": archivo_imagen,
                "texto": emparejamiento.texto_verdadero,
                "leido": emparejamiento.texto_leido,
                "similitud": round(emparejamiento.similitud, 3),
                "foto": nombre,
            }, ensure_ascii=False) + "\n")
        return len(emparejamientos), len(cajas)

    def _leer_recortes(self, imagen: Imagen, cajas: Sequence[CajaTexto]) -> list[str]:
        """Lectura aproximada de cada recorte; solo se usa para alinear."""
        resultado = self.motor.reconocer(imagen)
        if not resultado.lineas:
            return ["" for _ in cajas]

        textos = []
        for caja in cajas:
            mejor, mejor_solape = "", 0.0
            for linea in resultado.lineas:
                if linea.caja is None:
                    continue
                solape = self._solape_vertical(caja, linea.caja)
                if solape > mejor_solape:
                    mejor, mejor_solape = linea.texto, solape
            textos.append(mejor)
        return textos

    @staticmethod
    def _solape_vertical(a: CajaTexto, b: CajaTexto) -> float:
        inicio = max(a.y, b.y)
        fin = min(a.y + a.alto, b.y + b.alto)
        if fin <= inicio:
            return 0.0
        return (fin - inicio) / min(a.alto, b.alto)
