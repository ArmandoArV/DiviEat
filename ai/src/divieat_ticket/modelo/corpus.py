"""Corpus de renglones recortados por el pipeline real.

La CRNN entrenada con renglones renderizados ve, en produccion, algo distinto:
recortes de una foto corregida en perspectiva, enderezada y binarizada. Ese
salto de dominio es el que explica que tenga CER 0.009 en lineas sueltas y
falle en el ticket completo.

Aqui se cierra: se genera el ticket, se pasa por la **misma** cadena de
preproceso, se segmenta con el **mismo** segmentador y se guarda cada recorte
con su texto. Solo se aceptan los tickets donde el numero de recortes coincide
con el numero de renglones impresos; cuando no coincide no hay forma de saber
que texto le toca a cada recorte, y una etiqueta inventada es peor que no
tener el dato.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from divieat_ticket.modelo.alfabeto import Alfabeto
from divieat_ticket.ocr import Segmentador, SegmentadorMorfologico
from divieat_ticket.preproceso import CadenaDePreproceso
from divieat_ticket.sintetico import ConfiguracionSintetico, GeneradorTicketsSinteticos

ALTURA = 32
ANCHO_MAXIMO = 480


@dataclass
class EstadisticasCorpus:
    tickets_generados: int = 0
    tickets_aceptados: int = 0
    recortes: int = 0

    @property
    def rendimiento(self) -> float:
        return self.tickets_aceptados / self.tickets_generados if self.tickets_generados else 0.0

    def __str__(self) -> str:
        return (f"{self.recortes} recortes de {self.tickets_aceptados}/{self.tickets_generados} "
                f"tickets (rendimiento {self.rendimiento:.0%})")


class ConstructorDeCorpus:
    """Genera tickets y guarda los renglones que el pipeline sabe recortar."""

    def __init__(
        self,
        carpeta: str | Path,
        cadena: CadenaDePreproceso | None = None,
        segmentador: Segmentador | None = None,
        semilla: int = 23,
    ) -> None:
        self.carpeta = Path(carpeta)
        self.cadena = cadena or CadenaDePreproceso.por_defecto()
        self.segmentador = segmentador or SegmentadorMorfologico()
        self.generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=semilla))
        self.estadisticas = EstadisticasCorpus()

    def construir(self, recortes_objetivo: int, informar_cada: int = 25) -> EstadisticasCorpus:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        etiquetas = self.carpeta / "etiquetas.jsonl"
        with etiquetas.open("w", encoding="utf-8") as archivo:
            while self.estadisticas.recortes < recortes_objetivo:
                self.estadisticas.tickets_generados += 1
                for nombre, texto in self._de_un_ticket():
                    archivo.write(json.dumps({"imagen": nombre, "texto": texto},
                                             ensure_ascii=False) + "\n")
                    self.estadisticas.recortes += 1
                if self.estadisticas.tickets_generados % informar_cada == 0:
                    print(f"  {self.estadisticas}", flush=True)
        return self.estadisticas

    def _de_un_ticket(self) -> list[tuple[str, str]]:
        muestra = self.generador.generar()
        procesada = self.cadena.aplicar(muestra.imagen)
        cajas = self.segmentador.segmentar(procesada)
        if len(cajas) != len(muestra.renglones):
            return []                      # sin alineacion fiable, se descarta
        self.estadisticas.tickets_aceptados += 1

        salida = []
        indice_ticket = self.estadisticas.tickets_aceptados
        for posicion, (caja, texto) in enumerate(zip(cajas, muestra.renglones)):
            recorte = normalizar_recorte(caja.recortar(procesada).a_gris().matriz)
            nombre = f"t{indice_ticket:05d}_r{posicion:02d}.png"
            cv2.imwrite(str(self.carpeta / nombre), recorte)
            salida.append((nombre, texto))
        return salida


def normalizar_recorte(gris: np.ndarray, binarizar: bool = True) -> np.ndarray:
    """Lleva el recorte a 32 px de alto, binarizando por renglon.

    **Esta funcion es el contrato entre entrenamiento e inferencia.** El primer
    salto de dominio (CER 0.009 -> 0.272) nacio de que la red se entrenaba con
    renglones renderizados y en produccion recibia otra cosa. Para que no se
    repita, el corpus y `MotorCRNN` llaman aqui los dos.

    La binarizacion por recorte es mejor que una global: cada renglon elige su
    propio umbral, asi que una sombra que cruza la hoja deja de importar.
    """
    if binarizar and gris.size:
        gris = cv2.adaptiveThreshold(
            gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 11
        )
    alto, ancho = gris.shape
    escala = ALTURA / max(alto, 1)
    nuevo_ancho = max(8, min(ANCHO_MAXIMO, int(ancho * escala)))
    return cv2.resize(gris, (nuevo_ancho, ALTURA), interpolation=cv2.INTER_AREA)


class CorpusDeRenglones(Dataset):
    """Lee del disco los recortes producidos por `ConstructorDeCorpus`."""

    def __init__(
        self,
        carpeta: str | Path,
        alfabeto: Alfabeto | None = None,
        desde: float = 0.0,
        hasta: float = 1.0,
        aumentador: "AumentadorDeRecortes | None" = None,
    ) -> None:
        self.carpeta = Path(carpeta)
        self.alfabeto = alfabeto or Alfabeto.de_tickets()
        # Solo en entrenamiento: la validacion tiene que medir sobre el dato
        # tal cual, o deja de ser comparable entre epocas.
        self.aumentador = aumentador
        registros = [
            json.loads(linea)
            for linea in (self.carpeta / "etiquetas.jsonl").read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ]
        inicio, fin = int(len(registros) * desde), int(len(registros) * hasta)
        self.registros = registros[inicio:fin]

    def __len__(self) -> int:
        return len(self.registros)

    def __getitem__(self, indice: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        registro = self.registros[indice]
        gris = cv2.imread(str(self.carpeta / registro["imagen"]), cv2.IMREAD_GRAYSCALE)
        if self.aumentador is not None:
            gris = self.aumentador.aplicar(gris)
        texto = self.alfabeto.limpiar(registro["texto"])
        tensor = torch.from_numpy(1.0 - gris.astype(np.float32) / 255.0).unsqueeze(0)
        return tensor, torch.tensor(self.alfabeto.codificar(texto), dtype=torch.long), texto


class AumentadorDeRecortes:
    """Varia un recorte en cada epoca para que repetirlo no sea memorizarlo.

    Con un centenar de recortes reales, repetirlos identicos ocho veces lleva
    la perdida de entrenamiento a cero y la de validacion a ninguna parte: la
    red aprende esas imagenes, no la tarea. Aqui cada repeticion llega distinta
    —inclinada, mas gruesa, mas oscura, con otro ruido— asi que el modelo tiene
    que quedarse con lo que no cambia: las letras.

    Las deformaciones son pequenas a proposito. Un renglon de ticket esta ya
    enderezado y recortado por el segmentador; lo que varia en la realidad es
    la tinta, la luz y el grano, no la geometria.
    """

    def __init__(self, intensidad: float = 1.0) -> None:
        self.intensidad = intensidad

    def aplicar(self, gris: np.ndarray, azar: "random.Random | None" = None) -> np.ndarray:
        import random as _random

        azar = azar or _random.Random()
        matriz = gris
        if azar.random() < 0.5:
            matriz = self._inclinar(matriz, azar)
        if azar.random() < 0.45:
            matriz = self._estirar(matriz, azar)
        if azar.random() < 0.4:
            matriz = self._peso_de_tinta(matriz, azar)
        if azar.random() < 0.5:
            matriz = self._iluminacion(matriz, azar)
        if azar.random() < 0.45:
            matriz = self._desenfoque(matriz, azar)
        if azar.random() < 0.5:
            matriz = self._ruido(matriz, azar)
        return matriz

    def _inclinar(self, matriz, azar):
        alto, ancho = matriz.shape
        angulo = azar.uniform(-1.2, 1.2) * self.intensidad
        rotacion = cv2.getRotationMatrix2D((ancho / 2, alto / 2), angulo, 1.0)
        return cv2.warpAffine(matriz, rotacion, (ancho, alto), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)

    def _estirar(self, matriz, azar):
        """El ancho de caracter cambia entre impresoras y entre fotos."""
        alto, ancho = matriz.shape
        factor = 1.0 + azar.uniform(-0.06, 0.10) * self.intensidad
        nuevo = max(8, min(ANCHO_MAXIMO, int(ancho * factor)))
        return cv2.resize(matriz, (nuevo, alto), interpolation=cv2.INTER_LINEAR)

    def _peso_de_tinta(self, matriz, azar):
        nucleo = np.ones((2, 2), np.uint8)
        return (cv2.erode if azar.random() < 0.5 else cv2.dilate)(matriz, nucleo)

    def _iluminacion(self, matriz, azar):
        alfa = 1.0 + azar.uniform(-0.25, 0.25) * self.intensidad
        beta = azar.uniform(-25, 25) * self.intensidad
        return np.clip(matriz.astype(np.float32) * alfa + beta, 0, 255).astype(np.uint8)

    def _desenfoque(self, matriz, azar):
        return cv2.GaussianBlur(matriz, (3, 3), azar.uniform(0.2, 0.9))

    def _ruido(self, matriz, azar):
        sigma = azar.uniform(3, 14) * self.intensidad
        ruido = np.random.default_rng(azar.randrange(2**32)).normal(0, sigma, matriz.shape)
        return np.clip(matriz.astype(np.float32) + ruido, 0, 255).astype(np.uint8)
