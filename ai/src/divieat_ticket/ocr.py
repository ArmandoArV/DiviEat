"""Capa de reconocimiento de texto.

`MotorOCR` es la frontera: el pipeline no sabe si detras hay Tesseract,
EasyOCR o la CRNN propia entrenada con los tickets sinteticos. Eso permite
comparar motores con la misma metrica y cambiarlos sin tocar el parser.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Sequence

import cv2
import numpy as np

from divieat_ticket.imagen import Imagen


@dataclass(frozen=True)
class CajaTexto:
    """Rectangulo de una linea dentro de la imagen, en pixeles.

    Puede llevar el angulo del renglon. Sin preproceso global el texto llega
    inclinado dentro del recorte, y un renglon torcido es mucho mas dificil de
    leer para la CRNN; si quien segmenta conoce la orientacion, el recorte sale
    derecho sin enderezar la hoja entera.
    """

    x: int
    y: int
    ancho: int
    alto: int
    angulo: float = 0.0

    @property
    def centro_y(self) -> float:
        return self.y + self.alto / 2

    @property
    def centro(self) -> tuple[float, float]:
        return self.x + self.ancho / 2, self.y + self.alto / 2

    def recortar(self, imagen: Imagen) -> Imagen:
        if abs(self.angulo) < 0.3:
            return imagen.con(
                imagen.matriz[self.y : self.y + self.alto, self.x : self.x + self.ancho]
            )
        # Se rota alrededor del centro del renglon y despues se recorta, asi el
        # texto queda horizontal sin tocar el resto de la imagen.
        rotacion = cv2.getRotationMatrix2D(self.centro, self.angulo, 1.0)
        alto_total, ancho_total = imagen.matriz.shape[:2]
        girada = cv2.warpAffine(
            imagen.matriz, rotacion, (ancho_total, alto_total),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
        )
        return imagen.con(girada[self.y : self.y + self.alto, self.x : self.x + self.ancho])


@dataclass(frozen=True)
class LineaOCR:
    """Una linea reconocida, con su confianza."""

    texto: str
    confianza: float = 1.0
    caja: CajaTexto | None = None
    indice: int = 0

    def __str__(self) -> str:
        return f"[{self.indice:>2}] {self.confianza:4.2f} {self.texto}"


@dataclass
class ResultadoOCR:
    """Lo que devuelve un motor: lineas en orden de lectura."""

    lineas: list[LineaOCR] = field(default_factory=list)
    motor: str = "desconocido"

    def __iter__(self) -> Iterator[LineaOCR]:
        return iter(self.lineas)

    def __len__(self) -> int:
        return len(self.lineas)

    @property
    def texto(self) -> str:
        return "\n".join(linea.texto for linea in self.lineas)

    @property
    def confianza_media(self) -> float:
        if not self.lineas:
            return 0.0
        return sum(linea.confianza for linea in self.lineas) / len(self.lineas)


class MotorOCR(ABC):
    """Contrato de un reconocedor de texto."""

    @property
    def nombre(self) -> str:
        return type(self).__name__

    @abstractmethod
    def disponible(self) -> bool:
        """False si falta la dependencia; el pipeline puede elegir otro motor."""

    @abstractmethod
    def reconocer(self, imagen: Imagen) -> ResultadoOCR:
        ...

    def __repr__(self) -> str:
        estado = "ok" if self.disponible() else "no disponible"
        return f"<{self.nombre} ({estado})>"


class Segmentador(ABC):
    """Parte la imagen del ticket en renglones."""

    @property
    def nombre(self) -> str:
        return type(self).__name__

    @abstractmethod
    def segmentar(self, imagen: Imagen) -> list[CajaTexto]:
        ...

    @staticmethod
    def _tinta(imagen: Imagen) -> np.ndarray:
        """Binariza dejando el texto en blanco (255) sobre fondo negro."""
        gris = imagen.a_gris().matriz
        return cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]


class SegmentadorPorProyeccion(Segmentador):
    """Perfil de proyeccion horizontal: los valles separan los renglones.

    Tecnica clasica y barata, pero fragil: basta con un grado de inclinacion
    residual para que los valles se rellenen y dos renglones se fundan.
    """

    def __init__(self, alto_minimo: int = 12, umbral_tinta: float = 0.012) -> None:
        self.alto_minimo = alto_minimo
        self.umbral_tinta = umbral_tinta

    def segmentar(self, imagen: Imagen) -> list[CajaTexto]:
        tinta = self._tinta(imagen)
        perfil = tinta.sum(axis=1) / 255.0
        hay_texto = perfil > (self.umbral_tinta * imagen.ancho)

        cajas: list[CajaTexto] = []
        inicio: int | None = None
        for fila, ocupada in enumerate(hay_texto):
            if ocupada and inicio is None:
                inicio = fila
            elif not ocupada and inicio is not None:
                cajas.append(self._caja(tinta, inicio, fila, imagen.ancho))
                inicio = None
        if inicio is not None:
            cajas.append(self._caja(tinta, inicio, len(hay_texto), imagen.ancho))
        return [c for c in cajas if c.alto >= self.alto_minimo]

    @staticmethod
    def _caja(tinta: np.ndarray, desde: int, hasta: int, ancho_total: int) -> CajaTexto:
        franja = tinta[desde:hasta]
        columnas = np.where(franja.sum(axis=0) > 0)[0]
        if columnas.size == 0:
            return CajaTexto(0, desde, ancho_total, hasta - desde)
        x0, x1 = int(columnas[0]), int(columnas[-1])
        margen = 4
        x0 = max(0, x0 - margen)
        x1 = min(ancho_total - 1, x1 + margen)
        return CajaTexto(x0, max(0, desde - 2), x1 - x0 + 1, (hasta - desde) + 4)


class SegmentadorMorfologico(Segmentador):
    """Une los caracteres de un renglon con una dilatacion horizontal.

    Cada renglon se vuelve una mancha conectada y se recupera como contorno,
    asi que no depende de que las filas esten perfectamente horizontales: un
    renglon ligeramente inclinado sigue siendo una sola componente. Es mucho
    mas robusto que la proyeccion cuando la foto viene de una mesa.
    """

    def __init__(
        self,
        ancho_union: int = 25,
        alto_minimo: int = 10,
        ancho_minimo: int = 24,
        solapamiento_maximo: float = 0.6,   # fraccion de la altura tipica del renglon
        altura_relativa_minima: float = 0.55,
    ) -> None:
        self.ancho_union = ancho_union
        self.alto_minimo = alto_minimo
        self.ancho_minimo = ancho_minimo
        self.solapamiento_maximo = solapamiento_maximo
        self.altura_relativa_minima = altura_relativa_minima

    def segmentar(self, imagen: Imagen) -> list[CajaTexto]:
        tinta = self._tinta(imagen)
        nucleo = cv2.getStructuringElement(cv2.MORPH_RECT, (self.ancho_union, 1))
        unida = cv2.morphologyEx(tinta, cv2.MORPH_CLOSE, nucleo)
        unida = cv2.dilate(unida, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1)))

        contornos, _ = cv2.findContours(unida, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cajas = []
        for contorno in contornos:
            x, y, ancho, alto = cv2.boundingRect(contorno)
            if alto < self.alto_minimo or ancho < self.ancho_minimo:
                continue
            if alto > imagen.alto * 0.25:          # mancha gigante: no es un renglon
                continue
            cajas.append(CajaTexto(x, y, ancho, alto))
        cajas.sort(key=lambda c: c.centro_y)
        return self._descartar_reglas(self._agrupar_por_banda(cajas))

    def _descartar_reglas(self, cajas: list[CajaTexto]) -> list[CajaTexto]:
        """Quita las reglas de guiones y el borde del papel.

        Una linea de «-----» o el canto de la hoja son anchas y muy bajas
        comparadas con un renglon de texto. No aportan nada al OCR y, contadas
        como renglones, desalinean la correspondencia con el texto impreso.
        """
        if len(cajas) < 3:
            return cajas
        alto_tipico = float(np.median([c.alto for c in cajas]))
        return [c for c in cajas if c.alto >= self.altura_relativa_minima * alto_tipico]

    def _agrupar_por_banda(self, cajas: list[CajaTexto]) -> list[CajaTexto]:
        """Une todos los trozos que caen en la misma banda horizontal.

        Un renglon se parte en varias manchas cuando el hueco entre la
        descripcion y el importe supera la dilatacion. Comparar solo pares
        consecutivos no basta: hay renglones partidos en tres o mas. Se agrupa
        por cercania del centro vertical, usando la altura tipica del renglon
        como escala.
        """
        if not cajas:
            return []
        cajas = sorted(cajas, key=lambda c: c.centro_y)
        alto_tipico = float(np.median([c.alto for c in cajas]))
        tolerancia = max(4.0, alto_tipico * self.solapamiento_maximo)

        grupos: list[list[CajaTexto]] = [[cajas[0]]]
        for caja in cajas[1:]:
            centro_grupo = float(np.median([c.centro_y for c in grupos[-1]]))
            if abs(caja.centro_y - centro_grupo) <= tolerancia:
                grupos[-1].append(caja)
            else:
                grupos.append([caja])
        return [self._envolver(grupo) for grupo in grupos]

    @staticmethod
    def _envolver(grupo: list[CajaTexto]) -> CajaTexto:
        x0 = min(c.x for c in grupo)
        y0 = min(c.y for c in grupo)
        x1 = max(c.x + c.ancho for c in grupo)
        y1 = max(c.y + c.alto for c in grupo)
        return CajaTexto(x0, y0, x1 - x0, y1 - y0)


# Nombre historico: el resto del paquete pide "SegmentadorDeLineas".
SegmentadorDeLineas = SegmentadorMorfologico


class MotorDeReferencia(MotorOCR):
    """Oraculo: devuelve las lineas verdaderas, opcionalmente con ruido simulado.

    Sirve para desarrollar y medir el parser sin depender de ningun OCR real, y
    para separar el error de reconocimiento del error de interpretacion.
    """

    CONFUSIONES = {"0": "O", "O": "0", "1": "l", "l": "1", "5": "S", "S": "5", "8": "B"}

    def __init__(self, lineas: Sequence[str], tasa_error: float = 0.0, semilla: int = 0) -> None:
        self._lineas = list(lineas)
        self.tasa_error = tasa_error
        self._azar = np.random.default_rng(semilla)

    def disponible(self) -> bool:
        return True

    def reconocer(self, imagen: Imagen) -> ResultadoOCR:
        lineas = []
        for indice, texto in enumerate(self._lineas):
            sucio, confianza = self._ensuciar(texto)
            lineas.append(LineaOCR(texto=sucio, confianza=confianza, indice=indice))
        return ResultadoOCR(lineas=lineas, motor=self.nombre)

    def _ensuciar(self, texto: str) -> tuple[str, float]:
        if self.tasa_error <= 0:
            return texto, 1.0
        caracteres = list(texto)
        tocados = 0
        for posicion, caracter in enumerate(caracteres):
            if caracter in self.CONFUSIONES and self._azar.random() < self.tasa_error:
                caracteres[posicion] = self.CONFUSIONES[caracter]
                tocados += 1
        confianza = max(0.3, 1.0 - tocados * 0.12)
        return "".join(caracteres), confianza


class MotorTesseract(MotorOCR):
    """Adaptador de Tesseract via pytesseract (requiere el binario del sistema)."""

    def __init__(self, idioma: str = "spa+eng", psm: int = 6) -> None:
        self.idioma = idioma
        self.psm = psm

    def disponible(self) -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def reconocer(self, imagen: Imagen) -> ResultadoOCR:
        import pytesseract
        from pytesseract import Output

        datos = pytesseract.image_to_data(
            imagen.a_gris().matriz,
            lang=self.idioma,
            config=f"--psm {self.psm}",
            output_type=Output.DICT,
        )
        agrupadas: dict[tuple[int, int, int], list[int]] = {}
        for i, texto in enumerate(datos["text"]):
            if not texto.strip():
                continue
            clave = (datos["block_num"][i], datos["par_num"][i], datos["line_num"][i])
            agrupadas.setdefault(clave, []).append(i)

        lineas = []
        for indice, (_, posiciones) in enumerate(sorted(agrupadas.items())):
            palabras = [datos["text"][p] for p in posiciones]
            confianzas = [float(datos["conf"][p]) for p in posiciones if float(datos["conf"][p]) >= 0]
            x = min(datos["left"][p] for p in posiciones)
            y = min(datos["top"][p] for p in posiciones)
            ancho = max(datos["left"][p] + datos["width"][p] for p in posiciones) - x
            alto = max(datos["top"][p] + datos["height"][p] for p in posiciones) - y
            lineas.append(
                LineaOCR(
                    texto=" ".join(palabras),
                    confianza=(sum(confianzas) / len(confianzas) / 100) if confianzas else 0.0,
                    caja=CajaTexto(x, y, ancho, alto),
                    indice=indice,
                )
            )
        return ResultadoOCR(lineas=lineas, motor=self.nombre)


class MotorEasyOCR(MotorOCR):
    """Adaptador de EasyOCR (CRNN preentrenada; descarga pesos la primera vez)."""

    def __init__(self, idiomas: tuple[str, ...] = ("es",), usar_gpu: bool = False) -> None:
        self.idiomas = list(idiomas)
        self.usar_gpu = usar_gpu
        self._lector = None

    def disponible(self) -> bool:
        try:
            import easyocr  # noqa: F401

            return True
        except Exception:
            return False

    def _obtener_lector(self):
        if self._lector is None:
            import easyocr

            self._lector = easyocr.Reader(self.idiomas, gpu=self.usar_gpu, verbose=False)
        return self._lector

    def reconocer(self, imagen: Imagen) -> ResultadoOCR:
        detecciones = self._obtener_lector().readtext(imagen.a_gris().matriz)
        crudas = []
        for caja, texto, confianza in detecciones:
            xs = [int(p[0]) for p in caja]
            ys = [int(p[1]) for p in caja]
            crudas.append(
                (
                    CajaTexto(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
                    texto,
                    float(confianza),
                )
            )
        return ResultadoOCR(lineas=self._agrupar_en_renglones(crudas), motor=self.nombre)

    @staticmethod
    def _agrupar_en_renglones(crudas: list[tuple[CajaTexto, str, float]]) -> list[LineaOCR]:
        """EasyOCR devuelve fragmentos sueltos; los juntamos por banda vertical."""
        if not crudas:
            return []
        crudas.sort(key=lambda t: (t[0].centro_y, t[0].x))
        alto_tipico = np.median([c[0].alto for c in crudas])
        renglones: list[list[tuple[CajaTexto, str, float]]] = [[crudas[0]]]
        for caja, texto, confianza in crudas[1:]:
            if abs(caja.centro_y - renglones[-1][0][0].centro_y) <= alto_tipico * 0.6:
                renglones[-1].append((caja, texto, confianza))
            else:
                renglones.append([(caja, texto, confianza)])

        lineas = []
        for indice, renglon in enumerate(renglones):
            renglon.sort(key=lambda t: t[0].x)
            x = min(c.x for c, _, _ in renglon)
            y = min(c.y for c, _, _ in renglon)
            ancho = max(c.x + c.ancho for c, _, _ in renglon) - x
            alto = max(c.y + c.alto for c, _, _ in renglon) - y
            lineas.append(
                LineaOCR(
                    texto=" ".join(t for _, t, _ in renglon),
                    confianza=sum(c for _, _, c in renglon) / len(renglon),
                    caja=CajaTexto(x, y, ancho, alto),
                    indice=indice,
                )
            )
        return lineas


class SelectorDeMotor:
    """Elige el primer motor disponible de una lista de preferencia."""

    def __init__(self, motores: Sequence[MotorOCR]) -> None:
        self.motores = list(motores)

    def elegir(self) -> MotorOCR:
        for motor in self.motores:
            if motor.disponible():
                return motor
        raise RuntimeError(
            "ningun motor OCR disponible: instala pytesseract/easyocr "
            "o entrena la CRNN con `cli.py entrenar`"
        )

    def disponibles(self) -> list[MotorOCR]:
        return [m for m in self.motores if m.disponible()]


class MotorCRNN(MotorOCR):
    """Motor propio: segmenta renglones y los lee con la CRNN entrenada.

    A diferencia de Tesseract o EasyOCR, aqui controlamos las dos mitades:
    `SegmentadorDeLineas` decide donde empieza y termina cada renglon, y la red
    entrenada con tickets sinteticos transcribe cada recorte.
    """

    ALTURA = 32

    def __init__(
        self,
        ruta_modelo: str = "modelos/crnn.pt",
        segmentador: SegmentadorDeLineas | None = None,
        dispositivo: str | None = None,
        tamano_lote: int = 16,
    ) -> None:
        self.ruta_modelo = ruta_modelo
        self.segmentador = segmentador or SegmentadorDeLineas()
        self.dispositivo_pedido = dispositivo
        self.tamano_lote = tamano_lote
        self._modelo = None
        self._alfabeto = None
        self._decodificador = None
        self._dispositivo = None

    def disponible(self) -> bool:
        from pathlib import Path

        try:
            import torch  # noqa: F401
        except Exception:
            return False
        return Path(self.ruta_modelo).is_file()

    def _cargar(self) -> None:
        if self._modelo is not None:
            return
        import torch

        from divieat_ticket.modelo.ctc import DecodificadorVoraz
        from divieat_ticket.modelo.entrenamiento import EntrenadorCRNN, SelectorDeDispositivo

        self._dispositivo = SelectorDeDispositivo.elegir(self.dispositivo_pedido)
        self._modelo, self._alfabeto, _ = EntrenadorCRNN.cargar_modelo(
            self.ruta_modelo, self._dispositivo
        )
        self._decodificador = DecodificadorVoraz(self._alfabeto)
        self._torch = torch

    def reconocer(self, imagen: Imagen) -> ResultadoOCR:
        self._cargar()
        cajas = self.segmentador.segmentar(imagen)
        if not cajas:
            return ResultadoOCR(lineas=[], motor=self.nombre)

        recortes = [self._preparar(caja.recortar(imagen)) for caja in cajas]
        lineas: list[LineaOCR] = []
        for desde in range(0, len(recortes), self.tamano_lote):
            trozo = recortes[desde : desde + self.tamano_lote]
            lote = self._apilar(trozo)
            with self._torch.no_grad():
                salida = self._modelo(lote.to(self._dispositivo)).cpu()
            textos = self._decodificador.decodificar(salida)
            confianzas = self._decodificador.confianza(salida)
            for posicion, (texto, confianza) in enumerate(zip(textos, confianzas)):
                indice = desde + posicion
                lineas.append(
                    LineaOCR(
                        texto=texto,
                        confianza=float(confianza),
                        caja=cajas[indice],
                        indice=indice,
                    )
                )
        return ResultadoOCR(lineas=lineas, motor=self.nombre)

    def _preparar(self, recorte: Imagen) -> np.ndarray:
        """Exactamente la misma preparacion que uso el corpus de entrenamiento."""
        from divieat_ticket.modelo.corpus import normalizar_recorte

        redimensionado = normalizar_recorte(recorte.a_gris().matriz)
        return 1.0 - redimensionado.astype(np.float32) / 255.0

    def _apilar(self, recortes: list[np.ndarray]):
        ancho_maximo = max(r.shape[1] for r in recortes)
        lote = self._torch.zeros(len(recortes), 1, self.ALTURA, ancho_maximo)
        for posicion, recorte in enumerate(recortes):
            lote[posicion, 0, :, : recorte.shape[1]] = self._torch.from_numpy(recorte)
        return lote


class SegmentadorPorMotorOCR(Segmentador):
    """Usa como segmentador las cajas de renglon que devuelve un motor OCR.

    Sirve para **arrancar**: la U-Net propia se entreno con sinteticos y en
    fotos reales sub-segmenta la zona densa de productos, fundiendo la tabla
    entera en una sola mancha. Un motor que si funciona sobre fotos reales da
    cajas por renglon fiables, y con ellas se pueden etiquetar los recortes
    con los que despues se entrena el segmentador propio.
    """

    def __init__(self, motor: MotorOCR, alto_minimo: int = 10) -> None:
        self.motor = motor
        self.alto_minimo = alto_minimo

    def segmentar(self, imagen: Imagen) -> list[CajaTexto]:
        resultado = self.motor.reconocer(imagen)
        cajas = [
            l.caja for l in resultado.lineas
            if l.caja is not None and l.caja.alto >= self.alto_minimo
        ]
        if not cajas:
            return []
        return sorted(self._ancho_comun(cajas, imagen), key=lambda c: c.centro_y)

    @staticmethod
    def _ancho_comun(cajas: list[CajaTexto], imagen: Imagen) -> list[CajaTexto]:
        """Lleva todas las cajas al mismo rango horizontal.

        El motor acota cada caja al texto que *el* leyo, asi que en un renglon
        como «1    HORCHATA LATTE FRIO    $79.00» puede empezar en la
        descripcion y dejar fuera la columna de cantidad. La etiqueta si la
        incluye, y entrenar con esa discrepancia ensena a inventar cantidades.
        Un renglon de ticket ocupa el ancho del papel: se usa la union.
        """
        margen = 6
        x0 = max(0, min(c.x for c in cajas) - margen)
        x1 = min(imagen.ancho, max(c.x + c.ancho for c in cajas) + margen)
        return [CajaTexto(x0, c.y, x1 - x0, c.alto, c.angulo) for c in cajas]
