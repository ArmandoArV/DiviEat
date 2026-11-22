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
    """Produce textos plausibles de un renglon de ticket."""

    PLANTILLAS_NOTA = (
        "SON:{palabras} PESOS 00/100 M",
        "GRACIAS POR SU VISITA",
        "ESTE NO ES UN COMPROBANTE FISCAL",
        "PROPINA NO INCLUIDA",
        "LUGAR DE EXPEDICION",
        "CODIGO FACT: {codigo}",
        "DIAS VIGENCIA: {dias}",
        "***SOFT RESTAURANT V{version} PRO***",
        "https://mefacturo.mx/{slug}",
        "Si requiere factura, escanee el codigo QR o",
    )
    PALABRAS_MONTO = (
        "UN MIL CIENTO SETENTA Y CINCO", "CUATROCIENTOS VEINTIDOS",
        "UN MIL SEISCIENTOS CINCUENTA", "DOSCIENTOS OCHENTA",
    )
    NOMBRES = ("MAHOL", "DIEGO BRISENO", "RICARDO", "ANA LOPEZ", "71 RICARDO", "LUIS M")

    def __init__(self, azar: random.Random) -> None:
        self._azar = azar
        self._catalogo = CatalogoMexicano(azar)

    def una(self) -> str:
        """Elige un tipo de renglon con la frecuencia aproximada de un ticket real."""
        tipo = self._azar.choices(
            ["producto", "metadato", "fecha", "total", "encabezado", "nota"],
            weights=[46, 14, 8, 10, 10, 12],
        )[0]
        return getattr(self, f"_{tipo}")()

    def _producto(self) -> str:
        descripcion, unitario = self._azar.choice(self._catalogo.carta)
        cantidad = self._azar.choices([1, 2, 3, 4], weights=[7, 2, 1, 1])[0]
        importe = unitario * cantidad / 100
        relleno = self._azar.randint(3, 22)
        signo = "$" if self._azar.random() < 0.7 else ""
        return f"{cantidad}{' ' * self._azar.randint(1, 5)}{descripcion}{' ' * relleno}{signo}{importe:,.2f}"

    def _metadato(self) -> str:
        clave = self._azar.choice(["MESA", "MESERO", "PERSONAS", "ORDEN", "FOLIO", "CAJERO", "TEL"])
        separador = ":" if self._azar.random() < 0.7 else ": "
        if clave == "MESA":
            valor = self._azar.choice(["2Y7", "SALA4", "42", "A12", "7"])
        elif clave == "MESERO":
            valor = self._azar.choice(self.NOMBRES)
        elif clave == "PERSONAS":
            valor = str(self._azar.randint(1, 12))
        elif clave == "TEL":
            valor = str(self._azar.randrange(9_000_000_000, 9_999_999_999))
        elif clave == "CAJERO":
            valor = ""
        else:
            valor = str(self._azar.randrange(20, 999_999))
        return f"{clave}{separador}{valor}"

    def _fecha(self) -> str:
        dia, mes = self._azar.randint(1, 28), self._azar.randint(1, 12)
        hora, minuto, segundo = self._azar.randint(1, 12), self._azar.randint(0, 59), self._azar.randint(0, 59)
        meridiano = self._azar.choice(["AM", "PM"])
        return f"{dia:02d}/{mes:02d}/2026 {hora:02d}:{minuto:02d}:{segundo:02d} {meridiano}"

    def _total(self) -> str:
        monto = self._azar.randrange(15_000, 400_000) / 100
        estilo = self._azar.random()
        if estilo < 0.4:
            return f"TOTAL:{' ' * self._azar.randint(4, 14)}${monto:,.2f}"
        if estilo < 0.7:
            base = monto / 1.16
            return f"SUBTOTAL:${base:,.2f}{' ' * self._azar.randint(2, 6)}IVA:${monto - base:,.2f}"
        return f"IVA:{' ' * self._azar.randint(6, 16)}${monto * 0.16:,.2f}"

    def _encabezado(self) -> str:
        if self._azar.random() < 0.5:
            nombre, calle = self._catalogo.restaurante()
            return self._azar.choice([nombre, calle])
        return self._azar.choice(
            ["CANT. DESCRIPCION                  IMPORTE",
             "RFC:OMM200309S39", "IDA YUCATAN MEXICO CP 97000",
             "OPERADORA MONTES MOLINA", "RESTAURANTES MIYABI S. DE R.L.  DE C.V."]
        )

    def _nota(self) -> str:
        plantilla = self._azar.choice(self.PLANTILLAS_NOTA)
        return plantilla.format(
            palabras=self._azar.choice(self.PALABRAS_MONTO),
            codigo=f"{self._azar.randrange(10000, 99999)}LARAXGLF",
            dias=self._azar.choice(["7", "30", "ULTIMO DIA DEL MES"]),
            version=self._azar.choice(["11", "12"]),
            slug=self._azar.choice(["avelino", "marcelo", "miyabi"]),
        )


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
        margen = self._azar.randint(2, 8)
        ancho = int(fuente.getlength(texto)) + margen * 2
        alto = self.config.altura_render + margen * 2
        lienzo = Image.new("L", (max(ancho, 16), alto), color=self._azar.randint(238, 255))
        ImageDraw.Draw(lienzo).text(
            (margen, margen), texto, font=fuente, fill=self._azar.randint(10, 70)
        )
        matriz = np.array(lienzo)
        if self._azar.random() < self.config.probabilidad_degradar:
            matriz = self._degradar(matriz)
        return self._a_altura_fija(matriz)

    def _degradar(self, matriz: np.ndarray) -> np.ndarray:
        if self._azar.random() < 0.5:                      # impresion termica debil o saturada
            nucleo = np.ones((2, 2), np.uint8)
            matriz = (cv2.erode if self._azar.random() < 0.5 else cv2.dilate)(matriz, nucleo)
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
