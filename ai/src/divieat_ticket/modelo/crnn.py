"""CRNN: convolucionales para ver, recurrentes para leer.

Arquitectura clasica de reconocimiento de texto (Shi et al., 2015), que es el
cruce exacto de las clases 3 y 5 de Deep Learning:

    imagen (1 x 32 x W)
      -> ExtractorVisual   (CNN)      colapsa la altura a 1
      -> secuencia (T x B x 512)
      -> CabezaRecurrente  (BiLSTM)   contexto a izquierda y derecha
      -> logits (T x B x clases)      se entrena con CTC

La altura fija de 32 px es lo que permite que la CNN termine con altura 1; el
ancho queda libre, asi que la red lee renglones de cualquier largo.
"""

from __future__ import annotations

import torch
from torch import nn


class BloqueConvolucional(nn.Module):
    """Conv -> (BatchNorm) -> ReLU. La normalizacion estabiliza las capas hondas."""

    def __init__(
        self, entradas: int, salidas: int, nucleo: int = 3, paso: int = 1,
        relleno: int = 1, normalizar: bool = False,
    ) -> None:
        super().__init__()
        capas: list[nn.Module] = [nn.Conv2d(entradas, salidas, nucleo, paso, relleno)]
        if normalizar:
            capas.append(nn.BatchNorm2d(salidas))
        capas.append(nn.ReLU(inplace=True))
        self.bloque = nn.Sequential(*capas)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.bloque(x)


class ExtractorVisual(nn.Module):
    """Convierte la imagen en una secuencia de descriptores por columna.

    Los dos ultimos `MaxPool` usan paso (2,1): bajan la altura pero conservan
    el ancho, porque cada columna es un paso temporal para la CTC.
    """

    def __init__(self, canales_salida: int = 512) -> None:
        super().__init__()
        self.red = nn.Sequential(
            BloqueConvolucional(1, 64),
            nn.MaxPool2d(2, 2),                                   # 16 x W/2
            BloqueConvolucional(64, 128),
            nn.MaxPool2d(2, 2),                                   # 8 x W/4
            BloqueConvolucional(128, 256, normalizar=True),
            BloqueConvolucional(256, 256),
            nn.MaxPool2d((2, 2), (2, 1), (0, 1)),                 # 4 x W/4
            BloqueConvolucional(256, 512, normalizar=True),
            BloqueConvolucional(512, 512),
            nn.MaxPool2d((2, 2), (2, 1), (0, 1)),                 # 2 x W/4
            BloqueConvolucional(512, canales_salida, nucleo=2, relleno=0, normalizar=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(B,1,32,W) -> (T,B,C) con T = pasos de tiempo (columnas)."""
        mapa = self.red(x)
        if mapa.size(2) != 1:
            raise ValueError(
                f"la altura debe colapsar a 1 y quedo en {mapa.size(2)}; "
                "la imagen de entrada debe medir 32 px de alto"
            )
        mapa = mapa.squeeze(2)          # (B, C, T)
        return mapa.permute(2, 0, 1)    # (T, B, C)


class CabezaRecurrente(nn.Module):
    """Dos BiLSTM apiladas: cada columna se lee con el contexto de sus vecinas."""

    def __init__(self, entradas: int, ocultas: int, clases: int, capas: int = 2,
                 abandono: float = 0.1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            entradas, ocultas, num_layers=capas, bidirectional=True,
            dropout=abandono if capas > 1 else 0.0,
        )
        self.proyeccion = nn.Linear(ocultas * 2, clases)

    def forward(self, secuencia: torch.Tensor) -> torch.Tensor:
        salida, _ = self.lstm(secuencia)
        return self.proyeccion(salida)


class CRNN(nn.Module):
    """Red completa de reconocimiento de una linea de texto."""

    ALTURA_ENTRADA = 32

    def __init__(self, clases: int, ocultas: int = 256, canales: int = 512) -> None:
        super().__init__()
        self.clases = clases
        self.vision = ExtractorVisual(canales)
        self.lectura = CabezaRecurrente(canales, ocultas, clases)

    def forward(self, imagenes: torch.Tensor) -> torch.Tensor:
        """(B,1,32,W) -> log-probabilidades (T,B,clases), listas para CTCLoss."""
        secuencia = self.vision(imagenes)
        logits = self.lectura(secuencia)
        return nn.functional.log_softmax(logits, dim=2)

    def longitud_de_salida(self, ancho: int) -> int:
        """Pasos de tiempo que produce un ancho dado (para las longitudes de CTC)."""
        with torch.no_grad():
            sonda = torch.zeros(1, 1, self.ALTURA_ENTRADA, ancho)
            return self.vision(sonda).size(0)

    @property
    def parametros_entrenables(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
