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
    ) -> None:
        self.carpeta = Path(carpeta)
        self.alfabeto = alfabeto or Alfabeto.de_tickets()
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
        texto = self.alfabeto.limpiar(registro["texto"])
        tensor = torch.from_numpy(1.0 - gris.astype(np.float32) / 255.0).unsqueeze(0)
        return tensor, torch.tensor(self.alfabeto.codificar(texto), dtype=torch.long), texto
