"""Datos de entrenamiento para la CRNN: renglones sinteticos con su texto.

Un reconocedor de texto necesita pares (imagen de una linea, transcripcion).
No existe ese corpus para tickets mexicanos, asi que se fabrica imitando los
renglones que de verdad imprime el POS: productos con importe a la derecha,
metadatos `CLAVE:valor`, fechas de 12 horas, totales y notas al pie.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from torch.utils.data import Dataset

from divieat_ticket.modelo.alfabeto import Alfabeto
from divieat_ticket.sintetico import FUENTES_CANDIDATAS, CatalogoMexicano, FuenteNoDisponible


@dataclass(frozen=True)
class ConfiguracionLineas:
    altura: int = 32
    altura_render: int = 40
    ancho_maximo: int = 480
    semilla: int = 11
    probabilidad_degradar: float = 0.85


class FabricaDeTextos:
    """Produce renglones de ticket reales, componiendo con las mismas plantillas.

    Antes era una lista de plantillas escritas a mano, que se desviaba de lo
    que imprime el generador. Ahora se compone un ticket pequeno con
    `plantillas.py` y se toma un renglon al azar: componer es texto puro y
    cuesta microsegundos (lo caro es renderizar), asi que sale gratis
    garantizar que la CRNN entrene con **exactamente** los renglones que el
    sistema va a encontrar.
    """

    def __init__(self, azar: random.Random) -> None:
        self._azar = azar
        self._catalogo = CatalogoMexicano(azar)

    def una(self) -> str:
        from divieat_ticket.plantillas import CatalogoDePlantillas
        from divieat_ticket.sintetico import EstiloDeImporte

        ticket, contexto = self._ticket_corto()
        plantilla = CatalogoDePlantillas(self._azar).elegir()
        renglones = [
            texto
            for texto, _, _ in plantilla.componer(
                ticket, contexto, EstiloDeImporte.elegir(self._azar),
                self._azar.randint(38, 48),
            )
            if texto.strip() and set(texto.strip()) - set("-=_~.")
        ]
        return self._azar.choice(renglones) if renglones else "TOTAL: $0.00"

    def _ticket_corto(self):
        """Un ticket minimo: solo se necesita para extraer renglones."""
        from datetime import datetime, timedelta

        from divieat_ticket.dominio import Dinero, Producto, TicketExtraido
        from divieat_ticket.plantillas import ContextoDeTicket

        productos = [
            Producto(
                descripcion=descripcion,
                cantidad=self._azar.choices([1, 2, 3, 4], weights=[6, 3, 2, 1])[0],
                importe=Dinero(unitario * 2),
                precio_unitario=Dinero(unitario),
            )
            for descripcion, unitario in self._catalogo.muestra(self._azar.randint(2, 5))
        ]
        total = Dinero.suma(p.importe for p in productos)
        base = Dinero(int(round(total.centavos / 1.16)))
        nombre, direccion = self._catalogo.restaurante()
        apertura = datetime(2026, 1, 1, 9, 0) + timedelta(
            days=self._azar.randrange(330), minutes=self._azar.randrange(700)
        )
        ticket = TicketExtraido(
            productos=productos, restaurante=nombre, folio=str(self._azar.randrange(100, 999999)),
            subtotal=base, iva=total - base, total_impreso=total, fecha=apertura,
        )
        contexto = ContextoDeTicket(
            nombre=nombre, direccion=direccion,
            razon_social=self._azar.choice(CatalogoMexicano.RAZONES),
            rfc=f"{self._azar.choice('ABCDEFG')}{self._azar.randrange(100000, 999999)}XY1",
            telefono=str(self._azar.randrange(9_000_000_000, 9_999_999_999)),
            mesa=self._azar.choice(["2Y7", "SALA4", "33", "56", "7"]),
            mesero=self._azar.choice(CatalogoMexicano.MESEROS),
            comensales=self._azar.randint(1, 8), orden=self._azar.randrange(1, 300),
            apertura=apertura, cierre=apertura + timedelta(minutes=40),
            version_pos=self._azar.choice(["10", "11", "12"]),
            codigo_factura=f"{self._azar.randrange(10000, 99999)}LARAXGLF",
            sitio_factura=f"https://mefacturo.mx/{nombre.split()[-1].lower()}",
        )
        return ticket, contexto


class RenderizadorDeLinea:
    """Dibuja un texto como renglon de papel termico y lo degrada."""

    def __init__(self, config: ConfiguracionLineas, azar: random.Random) -> None:
        self.config = config
        self._azar = azar
        self._fuentes = self._cargar_fuentes(config.altura_render)

    @staticmethod
    def _cargar_fuentes(tamano: int) -> list[ImageFont.FreeTypeFont]:
        fuentes = []
        for ruta in FUENTES_CANDIDATAS:
            if Path(ruta).is_file():
                try:
                    fuentes.append(ImageFont.truetype(ruta, tamano))
                except OSError:
                    continue
        if not fuentes:
            raise FuenteNoDisponible("no hay tipografias monoespaciadas para entrenar")
        return fuentes

    def renderizar(self, texto: str) -> np.ndarray:
        fuente = self._azar.choice(self._fuentes)
        # Margenes asimetricos y amplios: el segmentador entrega el renglon con
        # el margen del papel a los lados, no recortado al texto. Entrenar solo
        # con texto pegado al borde hacia que el modelo leyera un «$» donde solo
        # habia papel en blanco.
        izquierda = self._azar.randint(2, 70)
        derecha = self._azar.randint(2, 50)
        vertical = self._azar.randint(2, 8)
        ancho = int(fuente.getlength(texto)) + izquierda + derecha
        alto = self.config.altura_render + vertical * 2
        lienzo = Image.new("L", (max(ancho, 16), alto), color=self._azar.randint(238, 255))
        ImageDraw.Draw(lienzo).text(
            (izquierda, vertical), texto, font=fuente, fill=self._azar.randint(10, 70)
        )
        matriz = np.array(lienzo)
        if self._azar.random() < self.config.probabilidad_degradar:
            matriz = self._degradar(matriz)
        return self._a_altura_fija(matriz)

    def _degradar(self, matriz: np.ndarray) -> np.ndarray:
        from divieat_ticket.sintetico import textura_termica

        if self._azar.random() < 0.5:                      # impresion termica debil o saturada
            nucleo = np.ones((2, 2), np.uint8)
            matriz = (cv2.erode if self._azar.random() < 0.5 else cv2.dilate)(matriz, nucleo)
        if self._azar.random() < 0.8:
            matriz = textura_termica(matriz, self._azar)
        if self._azar.random() < 0.6:
            matriz = cv2.GaussianBlur(matriz, (3, 3), self._azar.uniform(0.3, 1.2))
        if self._azar.random() < 0.6:
            sigma = self._azar.uniform(3, 14)
            ruido = np.random.default_rng(self._azar.randrange(2**32)).normal(0, sigma, matriz.shape)
            matriz = np.clip(matriz.astype(np.float32) + ruido, 0, 255).astype(np.uint8)
        if self._azar.random() < 0.4:                      # inclinacion residual del renglon
            alto, ancho = matriz.shape
            angulo = self._azar.uniform(-1.6, 1.6)
            giro = cv2.getRotationMatrix2D((ancho / 2, alto / 2), angulo, 1.0)
            matriz = cv2.warpAffine(matriz, giro, (ancho, alto), borderMode=cv2.BORDER_REPLICATE)
        if self._azar.random() < 0.3:                      # contraste despareja
            alfa = self._azar.uniform(0.65, 1.25)
            matriz = np.clip(matriz.astype(np.float32) * alfa, 0, 255).astype(np.uint8)
        return matriz

    def _a_altura_fija(self, matriz: np.ndarray) -> np.ndarray:
        alto, ancho = matriz.shape
        escala = self.config.altura / alto
        nuevo_ancho = max(8, min(self.config.ancho_maximo, int(ancho * escala)))
        return cv2.resize(matriz, (nuevo_ancho, self.config.altura), interpolation=cv2.INTER_AREA)


class ConjuntoLineas(Dataset):
    """Dataset sintetico reproducible: la muestra i siempre es la misma."""

    def __init__(
        self,
        cantidad: int,
        alfabeto: Alfabeto | None = None,
        config: ConfiguracionLineas | None = None,
        desplazamiento: int = 0,
    ) -> None:
        self.cantidad = cantidad
        self.alfabeto = alfabeto or Alfabeto.de_tickets()
        self.config = config or ConfiguracionLineas()
        self.desplazamiento = desplazamiento

    def __len__(self) -> int:
        return self.cantidad

    def __getitem__(self, indice: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        azar = random.Random(self.config.semilla + self.desplazamiento + indice)
        texto = self.alfabeto.limpiar(FabricaDeTextos(azar).una())
        matriz = RenderizadorDeLinea(self.config, azar).renderizar(texto)
        # tinta = 1, papel = 0: el relleno del lote con ceros queda como papel
        tensor = torch.from_numpy(1.0 - matriz.astype(np.float32) / 255.0).unsqueeze(0)
        return tensor, torch.tensor(self.alfabeto.codificar(texto), dtype=torch.long), texto


def agrupar_lote(muestras: list[tuple[torch.Tensor, torch.Tensor, str]]):
    """Collate: iguala anchos con relleno y concatena los objetivos para CTC."""
    imagenes, objetivos, textos = zip(*muestras)
    ancho_maximo = max(img.size(2) for img in imagenes)
    lote = torch.zeros(len(imagenes), 1, imagenes[0].size(1), ancho_maximo)
    for posicion, imagen in enumerate(imagenes):
        lote[posicion, :, :, : imagen.size(2)] = imagen
    longitudes = torch.tensor([len(o) for o in objetivos], dtype=torch.long)
    return lote, torch.cat(objetivos), longitudes, list(textos)
