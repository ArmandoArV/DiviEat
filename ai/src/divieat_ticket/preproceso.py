"""Preprocesamiento de la foto del ticket (material del curso de Recuperacion
de Informacion: procesamiento de imagenes, deteccion de bordes y umbralizacion).

Cada paso es una `OperacionImagen`; `CadenaDePreproceso` las compone. Asi se
puede reordenar, quitar o medir cada paso sin tocar los demas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

from divieat_ticket.imagen import Imagen


@dataclass(frozen=True)
class ConfiguracionPreproceso:
    """Perillas del preprocesamiento. Los valores por defecto salen de probar
    con los tickets sinteticos degradados de `sintetico.py`."""

    alto_objetivo: int = 1600
    area_minima_ticket: float = 0.20     # fraccion del area de la foto
    canny_bajo: int = 60
    canny_alto: int = 180
    bloque_umbral: int = 35              # debe ser impar
    constante_umbral: int = 11
    angulo_maximo_enderezado: float = 15.0


class OperacionImagen(ABC):
    """Un paso del preprocesamiento."""

    @property
    def nombre(self) -> str:
        return type(self).__name__

    @abstractmethod
    def aplicar(self, imagen: Imagen) -> Imagen:
        ...

    def aplicar_a_mascara(self, mascara: np.ndarray) -> np.ndarray:
        """Propaga a una mascara de etiquetas la geometria del ultimo `aplicar`.

        Las operaciones fotometricas no mueven pixeles y devuelven la mascara
        intacta; las geometricas reaplican su transformacion. Esto es lo que
        permite entrenar la U-Net sobre imagenes ya corregidas sin perder la
        supervision a nivel pixel.
        """
        return mascara

    def __call__(self, imagen: Imagen) -> Imagen:
        return self.aplicar(imagen)

    def __repr__(self) -> str:
        return f"<{self.nombre}>"


class EscalaDeGrises(OperacionImagen):
    def aplicar(self, imagen: Imagen) -> Imagen:
        return imagen.a_gris()


class EscaladoAAlto(OperacionImagen):
    """Normaliza la resolucion: el OCR es sensible al tamano de la letra."""

    def __init__(self, alto_objetivo: int) -> None:
        self.alto_objetivo = alto_objetivo
        self.ultimo_tamano: tuple[int, int] | None = None

    def aplicar(self, imagen: Imagen) -> Imagen:
        if imagen.alto == self.alto_objetivo:
            self.ultimo_tamano = imagen.dimensiones
            return imagen
        escala = self.alto_objetivo / imagen.alto
        interpolacion = cv2.INTER_AREA if escala < 1 else cv2.INTER_CUBIC
        self.ultimo_tamano = (max(1, int(imagen.ancho * escala)), self.alto_objetivo)
        return imagen.con(cv2.resize(imagen.matriz, self.ultimo_tamano, interpolation=interpolacion))

    def aplicar_a_mascara(self, mascara: np.ndarray) -> np.ndarray:
        if self.ultimo_tamano is None:
            return mascara
        return cv2.resize(mascara, self.ultimo_tamano, interpolation=cv2.INTER_NEAREST)


class ReduccionDeRuido(OperacionImagen):
    """Bilateral: quita grano de camara sin despeinar los bordes de las letras."""

    def __init__(self, diametro: int = 7, sigma_color: int = 55, sigma_espacio: int = 55) -> None:
        self.diametro = diametro
        self.sigma_color = sigma_color
        self.sigma_espacio = sigma_espacio

    def aplicar(self, imagen: Imagen) -> Imagen:
        return imagen.con(
            cv2.bilateralFilter(imagen.matriz, self.diametro, self.sigma_color, self.sigma_espacio)
        )


class CorreccionDePerspectiva(OperacionImagen):
    """Encuentra el cuadrilatero del papel y lo endereza (warp a vista frontal).

    Si no hay un contorno de cuatro lados lo bastante grande, devuelve la imagen
    intacta: preferimos no deformar una foto que ya estaba bien encuadrada.
    """

    def __init__(self, config: ConfiguracionPreproceso) -> None:
        self.config = config
        self.ultimo_cuadrilatero: np.ndarray | None = None
        self.ultima_homografia: np.ndarray | None = None
        self.ultimo_tamano: tuple[int, int] | None = None

    def aplicar(self, imagen: Imagen) -> Imagen:
        gris = imagen.a_gris().matriz
        suavizada = cv2.GaussianBlur(gris, (5, 5), 0)
        bordes = cv2.Canny(suavizada, self.config.canny_bajo, self.config.canny_alto)
        bordes = cv2.dilate(bordes, np.ones((3, 3), np.uint8), iterations=1)

        contornos, _ = cv2.findContours(bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area_foto = imagen.alto * imagen.ancho
        candidato = None
        for contorno in sorted(contornos, key=cv2.contourArea, reverse=True)[:8]:
            if cv2.contourArea(contorno) < self.config.area_minima_ticket * area_foto:
                break
            perimetro = cv2.arcLength(contorno, True)
            aprox = cv2.approxPolyDP(contorno, 0.02 * perimetro, True)
            if len(aprox) == 4:
                candidato = aprox.reshape(4, 2).astype(np.float32)
                break

        self.ultimo_cuadrilatero = candidato
        if candidato is None:
            self.ultima_homografia = None
            return imagen
        esquinas = self._ordenar_esquinas(candidato)
        self.ultima_homografia, self.ultimo_tamano = self._transformacion(esquinas)
        return imagen.con(
            cv2.warpPerspective(imagen.matriz, self.ultima_homografia, self.ultimo_tamano)
        )

    def aplicar_a_mascara(self, mascara: np.ndarray) -> np.ndarray:
        if self.ultima_homografia is None:
            return mascara
        return cv2.warpPerspective(
            mascara, self.ultima_homografia, self.ultimo_tamano, flags=cv2.INTER_NEAREST
        )

    @staticmethod
    def _transformacion(esquinas: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
        (si, sd, idr, ii) = esquinas
        ancho = max(1, int(max(np.linalg.norm(sd - si), np.linalg.norm(idr - ii))))
        alto = max(1, int(max(np.linalg.norm(ii - si), np.linalg.norm(idr - sd))))
        destino = np.array(
            [[0, 0], [ancho - 1, 0], [ancho - 1, alto - 1], [0, alto - 1]], dtype=np.float32
        )
        return cv2.getPerspectiveTransform(esquinas, destino), (ancho, alto)

    @staticmethod
    def _ordenar_esquinas(puntos: np.ndarray) -> np.ndarray:
        """Orden canonico: superior-izq, superior-der, inferior-der, inferior-izq."""
        suma = puntos.sum(axis=1)
        diferencia = np.diff(puntos, axis=1).ravel()
        return np.array(
            [
                puntos[np.argmin(suma)],
                puntos[np.argmin(diferencia)],
                puntos[np.argmax(suma)],
                puntos[np.argmax(diferencia)],
            ],
            dtype=np.float32,
        )

    @staticmethod
    def _enderezar(matriz: np.ndarray, esquinas: np.ndarray) -> np.ndarray:
        (si, sd, idr, ii) = esquinas
        ancho = int(max(np.linalg.norm(sd - si), np.linalg.norm(idr - ii)))
        alto = int(max(np.linalg.norm(ii - si), np.linalg.norm(idr - sd)))
        ancho, alto = max(ancho, 1), max(alto, 1)
        destino = np.array(
            [[0, 0], [ancho - 1, 0], [ancho - 1, alto - 1], [0, alto - 1]], dtype=np.float32
        )
        transformacion = cv2.getPerspectiveTransform(esquinas, destino)
        return cv2.warpPerspective(matriz, transformacion, (ancho, alto))


class Enderezado(OperacionImagen):
    """Corrige la inclinacion residual estimando el angulo del bloque de texto."""

    def __init__(self, angulo_maximo: float = 15.0) -> None:
        self.angulo_maximo = angulo_maximo
        self.ultimo_angulo: float = 0.0

    def aplicar(self, imagen: Imagen) -> Imagen:
        gris = imagen.a_gris().matriz
        tinta = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coordenadas = np.column_stack(np.where(tinta > 0))
        if coordenadas.shape[0] < 50:
            self.ultimo_angulo = 0.0
            return imagen

        angulo = cv2.minAreaRect(coordenadas[:, ::-1].astype(np.float32))[-1]
        if angulo > 45:
            angulo -= 90
        if abs(angulo) > self.angulo_maximo:
            self.ultimo_angulo = 0.0
            return imagen

        self.ultimo_angulo = float(angulo)
        centro = (imagen.ancho / 2, imagen.alto / 2)
        rotacion = cv2.getRotationMatrix2D(centro, angulo, 1.0)
        return imagen.con(
            cv2.warpAffine(
                imagen.matriz, rotacion, imagen.dimensiones,
                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
            )
        )


class EnderezadoPorProyeccion(OperacionImagen):
    """Busca el angulo que deja los renglones mas horizontales.

    Para cada angulo candidato se rota la imagen y se mide la **varianza del
    perfil de proyeccion horizontal**: cuando los renglones estan alineados,
    cada fila esta llena de tinta o completamente vacia, asi que la varianza se
    dispara. Es el metodo clasico de enderezado de documentos y, a diferencia
    de `minAreaRect`, no se deja enganar por el borde del papel ni por una
    mancha suelta: mide el texto como conjunto.
    """

    def __init__(self, rango: float = 5.0, paso: float = 0.2, ancho_analisis: int = 500) -> None:
        self.rango = rango
        self.paso = paso
        self.ancho_analisis = ancho_analisis
        self.ultimo_angulo: float = 0.0
        self.ultima_rotacion: np.ndarray | None = None
        self.ultimo_tamano: tuple[int, int] | None = None

    def aplicar(self, imagen: Imagen) -> Imagen:
        angulo = self.estimar(imagen)
        self.ultimo_angulo = angulo
        self.ultimo_tamano = imagen.dimensiones
        if abs(angulo) < self.paso / 2:
            self.ultima_rotacion = None
            return imagen
        centro = (imagen.ancho / 2, imagen.alto / 2)
        self.ultima_rotacion = cv2.getRotationMatrix2D(centro, angulo, 1.0)
        return imagen.con(
            cv2.warpAffine(
                imagen.matriz, self.ultima_rotacion, imagen.dimensiones,
                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
            )
        )

    def aplicar_a_mascara(self, mascara: np.ndarray) -> np.ndarray:
        if self.ultima_rotacion is None:
            return mascara
        return cv2.warpAffine(
            mascara, self.ultima_rotacion, self.ultimo_tamano,
            flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )

    def estimar(self, imagen: Imagen) -> float:
        """Angulo en grados que maximiza la nitidez del perfil de proyeccion."""
        gris = imagen.a_gris().matriz
        escala = min(1.0, self.ancho_analisis / max(gris.shape[1], 1))
        if escala < 1.0:
            gris = cv2.resize(gris, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
        tinta = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        if tinta.sum() == 0:
            return 0.0

        alto, ancho = tinta.shape
        centro = (ancho / 2, alto / 2)
        mejor_angulo, mejor_puntaje = 0.0, -1.0
        pasos = int(self.rango / self.paso)
        for indice in range(-pasos, pasos + 1):
            angulo = indice * self.paso
            if angulo == 0:
                girada = tinta
            else:
                rotacion = cv2.getRotationMatrix2D(centro, angulo, 1.0)
                girada = cv2.warpAffine(
                    tinta, rotacion, (ancho, alto), flags=cv2.INTER_NEAREST,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0,
                )
            puntaje = float(np.var(girada.sum(axis=1, dtype=np.float64)))
            if puntaje > mejor_puntaje:
                mejor_angulo, mejor_puntaje = angulo, puntaje
        return mejor_angulo


class BinarizacionAdaptativa(OperacionImagen):
    """Umbral por vecindad: aguanta la iluminacion despareja de una mesa."""

    def __init__(self, bloque: int = 35, constante: int = 11) -> None:
        self.bloque = bloque if bloque % 2 == 1 else bloque + 1
        self.constante = constante

    def aplicar(self, imagen: Imagen) -> Imagen:
        gris = imagen.a_gris().matriz
        return imagen.con(
            cv2.adaptiveThreshold(
                gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
                self.bloque, self.constante,
            )
        )


class CadenaDePreproceso:
    """Composite de operaciones. Guarda trazas para poder auditar cada paso."""

    def __init__(self, operaciones: list[OperacionImagen]) -> None:
        self.operaciones = operaciones

    @classmethod
    def por_defecto(cls, config: ConfiguracionPreproceso | None = None) -> "CadenaDePreproceso":
        config = config or ConfiguracionPreproceso()
        return cls(
            [
                EscaladoAAlto(config.alto_objetivo),
                ReduccionDeRuido(),
                CorreccionDePerspectiva(config),
                EscalaDeGrises(),
                EnderezadoPorProyeccion(config.angulo_maximo_enderezado),
                BinarizacionAdaptativa(config.bloque_umbral, config.constante_umbral),
            ]
        )

    def aplicar(self, imagen: Imagen) -> Imagen:
        for operacion in self.operaciones:
            imagen = operacion.aplicar(imagen)
        return imagen

    def aplicar_con_mascara(
        self, imagen: Imagen, mascara: np.ndarray
    ) -> tuple[Imagen, np.ndarray]:
        """Aplica la cadena a la imagen y arrastra la mascara por la geometria."""
        for operacion in self.operaciones:
            imagen = operacion.aplicar(imagen)
            mascara = operacion.aplicar_a_mascara(mascara)
        return imagen, mascara

    def aplicar_con_trazas(self, imagen: Imagen) -> list[tuple[str, Imagen]]:
        """Devuelve [(nombre_paso, imagen_resultante)] incluyendo la original."""
        trazas = [("original", imagen)]
        for operacion in self.operaciones:
            imagen = operacion.aplicar(imagen)
            trazas.append((operacion.nombre, imagen))
        return trazas

    def __len__(self) -> int:
        return len(self.operaciones)

    def __repr__(self) -> str:
        return " -> ".join(o.nombre for o in self.operaciones)
