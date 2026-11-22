"""Envoltorio de imagen: aisla a OpenCV del resto del paquete."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ErrorDeImagen(RuntimeError):
    """No se pudo leer, escribir o interpretar una imagen."""


class Imagen:
    """Una imagen en memoria. Inmutable en la practica: cada operacion devuelve otra."""

    def __init__(self, matriz: np.ndarray, origen: str | None = None) -> None:
        if matriz is None or matriz.size == 0:
            raise ErrorDeImagen("matriz de imagen vacia")
        self._matriz = matriz
        self.origen = origen

    # ---------------------------------------------------------------- fabricas
    @classmethod
    def desde_archivo(cls, ruta: str | Path) -> "Imagen":
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorDeImagen(f"no existe el archivo {ruta}")
        matriz = cv2.imread(str(ruta), cv2.IMREAD_COLOR)
        if matriz is None:
            raise ErrorDeImagen(f"OpenCV no pudo decodificar {ruta}")
        return cls(matriz, origen=str(ruta))

    @classmethod
    def desde_pil(cls, imagen_pil, origen: str | None = None) -> "Imagen":
        matriz = np.array(imagen_pil.convert("RGB"))
        return cls(cv2.cvtColor(matriz, cv2.COLOR_RGB2BGR), origen=origen)

    # -------------------------------------------------------------- propiedades
    @property
    def matriz(self) -> np.ndarray:
        return self._matriz

    @property
    def alto(self) -> int:
        return self._matriz.shape[0]

    @property
    def ancho(self) -> int:
        return self._matriz.shape[1]

    @property
    def es_gris(self) -> bool:
        return self._matriz.ndim == 2

    @property
    def dimensiones(self) -> tuple[int, int]:
        return self.ancho, self.alto

    # -------------------------------------------------------------- operaciones
    def con(self, matriz: np.ndarray) -> "Imagen":
        """Nueva Imagen con la misma procedencia pero otra matriz."""
        return Imagen(matriz, origen=self.origen)

    def a_gris(self) -> "Imagen":
        if self.es_gris:
            return self
        return self.con(cv2.cvtColor(self._matriz, cv2.COLOR_BGR2GRAY))

    def a_color(self) -> "Imagen":
        if not self.es_gris:
            return self
        return self.con(cv2.cvtColor(self._matriz, cv2.COLOR_GRAY2BGR))

    def a_pil(self):
        from PIL import Image

        if self.es_gris:
            return Image.fromarray(self._matriz)
        return Image.fromarray(cv2.cvtColor(self._matriz, cv2.COLOR_BGR2RGB))

    def guardar(self, ruta: str | Path) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(ruta), self._matriz):
            raise ErrorDeImagen(f"no se pudo escribir {ruta}")
        return ruta

    def __repr__(self) -> str:
        tipo = "gris" if self.es_gris else "color"
        return f"<Imagen {self.ancho}x{self.alto} {tipo}>"
