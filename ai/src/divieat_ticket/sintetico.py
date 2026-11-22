"""Generador de tickets sinteticos con verdad de referencia.

No existe un corpus publico de tickets de restaurante mexicano, asi que lo
fabricamos: renderizamos el ticket desde un `TicketExtraido` conocido y luego
lo degradamos como lo degradaria una foto en una mesa (angulo, sombra, ruido,
desenfoque, compresion). La verdad de referencia sale gratis, y con ella se
puede entrenar el reconocedor y medir el error de punta a punta.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from divieat_ticket.dominio import Dinero, Producto, TicketExtraido
from divieat_ticket.imagen import Imagen

FUENTES_CANDIDATAS = (
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/Library/Fonts/Courier New.ttf",
)


class FuenteNoDisponible(RuntimeError):
    """No se encontro ninguna tipografia monoespaciada en el sistema."""


class EstiloDeImporte:
    """Como imprime los importes un POS concreto.

    Los cinco tickets reales que tenemos usan simbolo siempre: pegado
    (`$160.00`) o en su propia columna (`$     75.00`). El estilo no cambia
    dentro de un mismo ticket, asi que se elige una vez y se respeta.
    """

    PEGADO = "pegado"
    COLUMNA = "columna"
    SIN_SIMBOLO = "sin"

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre

    @classmethod
    def elegir(cls, azar: random.Random) -> "EstiloDeImporte":
        return cls(azar.choices(
            [cls.PEGADO, cls.COLUMNA, cls.SIN_SIMBOLO], weights=[62, 30, 8]
        )[0])

    def formatear(self, importe: Dinero) -> str:
        monto = f"{importe.pesos:,.2f}"
        if self.nombre == self.PEGADO:
            return f"${monto}"
        if self.nombre == self.COLUMNA:
            return f"$  {monto:>10}"
        return monto


@dataclass(frozen=True)
class ConfiguracionSintetico:
    ancho_papel: int = 620
    margen: int = 34
    tam_fuente: int = 21
    interlineado: int = 32
    semilla: int = 7
    productos_min: int = 4
    productos_max: int = 12
    probabilidad_propina: float = 0.4


class CatalogoMexicano:
    """Carta plausible de un restaurante mexicano, con precios en centavos."""

    PLATILLOS: tuple[tuple[str, int], ...] = (
        ("TACOS DE PASTOR", 6000), ("TACOS DE SUADERO", 5500), ("FLAUTAS DE POLLO", 14500),
        ("QUESADILLAS", 6500), ("GUACAMOLE", 12000), ("SOPA DE TORTILLA", 9500),
        ("ENCHILADAS VERDES", 15500), ("CHILAQUILES ROJOS", 13500), ("POZOLE", 16500),
        ("ARRACHERA 300G", 32000), ("PESCADO ZARANDEADO", 28500), ("ESQUITES", 5500),
        ("CEVICHE DE CAMARON", 21000), ("ALAMBRE DE RES", 19500), ("TORTA AHOGADA", 11000),
        ("FLAN NAPOLITANO", 12000), ("PASTEL TRES LECHES", 11500), ("CHURROS", 7500),
    )
    BEBIDAS: tuple[tuple[str, int], ...] = (
        ("AGUA DE HORCHATA", 5500), ("AGUA DE JAMAICA", 5500), ("MICHELADA", 9500),
        ("CERVEZA CLARA", 7500), ("CERVEZA OSCURA", 8000), ("REFRESCO", 4500),
        ("CAFE DE OLLA", 5000), ("MARGARITA", 14500), ("MEZCAL DERECHO", 16000),
    )
    RESTAURANTES: tuple[str, ...] = (
        "LA NORTESTENSE", "FONDA DONA MARU", "EL TIZONCITO DEL SUR", "MARISCOS EL FARO",
        "TAQUERIA LOS COMPAS", "COCINA DE HUMO",
    )
    CALLES: tuple[str, ...] = (
        "AV. REVOLUCION 120 COL. CENTRO MERIDA YUCATAN MEXICO CP 97000",
        "CALZ. DE TLALPAN 455 COL. PORTALES CIUDAD DE MEXICO CP 03300",
        "CALLE 56 A NO. 469 ENTRE 35 Y 37 COL. CENTRO MERIDA YUCATAN CP 97000",
        "AV. DIEGO DE ORDAZ 22 COL. REAL DE SAN JOSE JIUTEPEC MORELOS CP 62563",
        "PRIVADA SINALOA NUM.1, AVENIDA SAN DIEGO, COLONIA VISTA HERMOSA CP 62290",
    )
    RAZONES: tuple[str, ...] = (
        "OPERADORA MONTES MOLINA", "GRUPO GUAVOS", "RESTAURANTES DEL SURESTE S.A. DE C.V.",
        "ALIMENTOS Y SERVICIOS SA DE CV", "GRUPO GASTRONOMICO PENINSULAR",
    )
    MESEROS: tuple[str, ...] = (
        "MAHOL", "DIEGO BRISENO", "LETICIA ARCADEO MEJIA", "71 RICARDO", "LUIS",
        "ANA LOPEZ", "J. CARLOS", "MARTHA R",
    )

    def __init__(self, azar: random.Random) -> None:
        self._azar = azar

    @property
    def carta(self) -> tuple[tuple[str, int], ...]:
        return self.PLATILLOS + self.BEBIDAS

    def muestra(self, cantidad: int) -> list[tuple[str, int]]:
        return self._azar.sample(self.carta, k=min(cantidad, len(self.carta)))

    def restaurante(self) -> tuple[str, str]:
        return self._azar.choice(self.RESTAURANTES), self._azar.choice(self.CALLES)


class RenderizadorTicket:
    """Dibuja un `TicketExtraido` como papel termico limpio."""

    def __init__(self, config: ConfiguracionSintetico) -> None:
        self.config = config
        self.fuente = self._cargar_fuente(config.tam_fuente)
        self.fuente_titulo = self._cargar_fuente(int(config.tam_fuente * 1.45))

    @staticmethod
    def _cargar_fuente(tamano: int) -> ImageFont.FreeTypeFont:
        for ruta in FUENTES_CANDIDATAS:
            if Path(ruta).is_file():
                try:
                    return ImageFont.truetype(ruta, tamano)
                except OSError:
                    continue
        raise FuenteNoDisponible(
            "no encontre una tipografia monoespaciada; instala DejaVu Sans Mono"
        )

    def lineas_de_texto(
        self, ticket: TicketExtraido, contexto, estilo=None, plantilla=None
    ) -> list[str]:
        """Los renglones que se van a imprimir, en orden y sin los vacios.

        Es la etiqueta de cada recorte cuando se entrena con la segmentacion
        real: el renglon n-esimo que detecta el segmentador corresponde al
        n-esimo texto no vacio que se dibujo.
        """
        return [
            texto
            for texto, _, _ in self._componer(ticket, contexto, estilo, plantilla)
            if texto.strip() and not self._es_separador(texto)
        ]

    @staticmethod
    def _es_separador(texto: str) -> bool:
        """Las reglas de guiones no son renglones de texto: el segmentador las
        descarta por altura, asi que tampoco deben contar como etiqueta."""
        limpio = texto.strip()
        return bool(limpio) and set(limpio) <= set("-=_~.")

    def renderizar(
        self, ticket: TicketExtraido, contexto, estilo=None, plantilla=None
    ) -> Image.Image:
        return self.renderizar_con_cajas(ticket, contexto, estilo, plantilla)[0]

    def renderizar_con_cajas(
        self, ticket: TicketExtraido, contexto, estilo=None, plantilla=None
    ) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
        """Dibuja el ticket y devuelve la caja (x, y, ancho, alto) de cada renglon.

        Son las cajas de los renglones que cuentan como texto: las reglas de
        guiones y los vacios quedan fuera, igual que en `lineas_de_texto`. Es
        la supervision a nivel pixel para la segmentacion.
        """
        lineas = self._componer(ticket, contexto, estilo, plantilla)
        alto = self.config.margen * 2 + self.config.interlineado * len(lineas)
        lienzo = Image.new("L", (self.config.ancho_papel, alto), color=250)
        pincel = ImageDraw.Draw(lienzo)

        cajas: list[tuple[int, int, int, int]] = []
        y = self.config.margen
        for texto, centrado, titulo in lineas:
            fuente = self.fuente_titulo if titulo else self.fuente
            ancho_texto = pincel.textlength(texto, font=fuente)
            x = (self.config.ancho_papel - ancho_texto) / 2 if centrado else self.config.margen
            pincel.text((x, y), texto, font=fuente, fill=25)
            if texto.strip() and not self._es_separador(texto):
                alto_glifo = int(self.config.tam_fuente * (1.45 if titulo else 1.0))
                cajas.append((int(x), int(y), max(1, int(ancho_texto)), alto_glifo))
            y += self.config.interlineado
        return lienzo, cajas

    def _componer(self, ticket, contexto, estilo, plantilla):
        from divieat_ticket.plantillas import PlantillaGenerica

        estilo = estilo or EstiloDeImporte(EstiloDeImporte.PEGADO)
        plantilla = plantilla or PlantillaGenerica()
        return plantilla.componer(ticket, contexto, estilo, self._columnas())

    def _columnas(self) -> int:
        util = self.config.ancho_papel - self.config.margen * 2
        ancho_caracter = self.fuente.getlength("M") or 10
        return max(24, int(util / ancho_caracter))


class Degradacion:
    """Un deterioro fotografico aplicable al papel renderizado."""

    def __init__(self, azar: random.Random) -> None:
        self._azar = azar

    @property
    def nombre(self) -> str:
        return type(self).__name__

    def aplicar(
        self, matriz: np.ndarray, mascara: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray | None]:
        """Devuelve (imagen, mascara). Las degradaciones fotometricas no tocan
        la mascara; las geometricas le aplican la misma transformacion."""
        raise NotImplementedError


class TintaTermica(Degradacion):
    """Imita la impresion termica: trazo que engorda o se adelgaza.

    La cabeza termica marca mas o menos segun la temperatura y lo gastado del
    papel. Es la diferencia visible entre una fuente renderizada limpia y un
    ticket de verdad, y es justo donde la red entrenada solo con texto
    renderizado dejaba de transferir.
    """

    def aplicar(self, matriz, mascara=None):
        eleccion = self._azar.random()
        nucleo = np.ones((2, 2), np.uint8)
        if eleccion < 0.4:
            matriz = cv2.erode(matriz, nucleo)        # trazo grueso (tinta de mas)
        elif eleccion < 0.7:
            matriz = cv2.dilate(matriz, nucleo)       # trazo debil (papel gastado)
        return matriz, mascara


class SombraDespareja(Degradacion):
    """Gradiente suave: la lampara de la mesa nunca ilumina parejo."""

    def aplicar(self, matriz, mascara=None):
        alto, ancho = matriz.shape[:2]
        eje_x = np.linspace(self._azar.uniform(0.55, 1.0), self._azar.uniform(0.55, 1.0), ancho)
        eje_y = np.linspace(self._azar.uniform(0.6, 1.0), self._azar.uniform(0.6, 1.0), alto)
        mascara_luz = np.outer(eje_y, eje_x)
        return np.clip(matriz.astype(np.float32) * mascara_luz, 0, 255).astype(np.uint8), mascara

class RuidoDeSensor(Degradacion):
    def aplicar(self, matriz, mascara=None):
        sigma = self._azar.uniform(3, 11)
        ruido = np.random.default_rng(self._azar.randrange(2**32)).normal(0, sigma, matriz.shape)
        return np.clip(matriz.astype(np.float32) + ruido, 0, 255).astype(np.uint8), mascara

class DesenfoqueDeCamara(Degradacion):
    def aplicar(self, matriz, mascara=None):
        radio = self._azar.choice([1, 1, 3, 3, 5])
        return cv2.GaussianBlur(matriz, (radio, radio), 0), mascara

class PerspectivaDeMesa(Degradacion):
    """Mete el papel en una escena mas grande, inclinado como una foto real."""

    def aplicar(self, matriz, mascara=None):
        alto, ancho = matriz.shape[:2]
        margen_x, margen_y = int(ancho * 0.16), int(alto * 0.08)
        forma = (alto + margen_y * 2, ancho + margen_x * 2)

        origen = np.float32(
            [[margen_x, margen_y], [margen_x + ancho, margen_y],
             [margen_x + ancho, margen_y + alto], [margen_x, margen_y + alto]]
        )
        desvio = min(forma[1], forma[0]) * 0.035
        destino = origen + np.float32(
            [[self._azar.uniform(-desvio, desvio) for _ in range(2)] for _ in range(4)]
        )
        homografia = cv2.getPerspectiveTransform(origen, destino)
        angulo = self._azar.uniform(-6, 6)
        giro = cv2.getRotationMatrix2D((forma[1] / 2, forma[0] / 2), angulo, 1.0)

        imagen = self._transformar(matriz, forma, margen_x, margen_y, homografia, giro, 150, cv2.INTER_LINEAR)
        if mascara is None:
            return imagen, None
        # La mascara viaja con la misma homografia y el mismo giro, en vecino
        # mas cercano para que siga siendo binaria.
        return imagen, self._transformar(mascara, forma, margen_x, margen_y, homografia, giro, 0, cv2.INTER_NEAREST)

    @staticmethod
    def _transformar(matriz, forma, margen_x, margen_y, homografia, giro, relleno, interpolacion):
        alto, ancho = matriz.shape[:2]
        lienzo = np.full(forma, relleno, np.uint8)
        lienzo[margen_y:margen_y + alto, margen_x:margen_x + ancho] = matriz
        inclinado = cv2.warpPerspective(
            lienzo, homografia, (forma[1], forma[0]), flags=interpolacion,
            borderMode=cv2.BORDER_CONSTANT, borderValue=relleno,
        )
        return cv2.warpAffine(
            inclinado, giro, (forma[1], forma[0]), flags=interpolacion,
            borderMode=cv2.BORDER_CONSTANT, borderValue=relleno,
        )


class CompresionJPEG(Degradacion):
    def aplicar(self, matriz, mascara=None):
        calidad = self._azar.randrange(45, 92)
        ok, buffer = cv2.imencode(".jpg", matriz, [int(cv2.IMWRITE_JPEG_QUALITY), calidad])
        return (cv2.imdecode(buffer, cv2.IMREAD_GRAYSCALE) if ok else matriz), mascara

@dataclass
class MuestraSintetica:
    """Par (imagen, verdad) listo para entrenar o evaluar."""

    imagen: Imagen
    verdad: TicketExtraido
    limpia: Imagen
    degradaciones: list[str] = field(default_factory=list)
    renglones: list[str] = field(default_factory=list)
    mascara: np.ndarray | None = None

    def guardar(self, carpeta: str | Path, nombre: str) -> tuple[Path, Path]:
        carpeta = Path(carpeta)
        ruta_imagen = self.imagen.guardar(carpeta / f"{nombre}.jpg")
        ruta_verdad = carpeta / f"{nombre}.json"
        ruta_verdad.write_text(self.verdad.a_json(), encoding="utf-8")
        return ruta_imagen, ruta_verdad


class GeneradorTicketsSinteticos:
    """Fabrica tickets con verdad de referencia, de forma reproducible."""

    def __init__(self, config: ConfiguracionSintetico | None = None) -> None:
        self.config = config or ConfiguracionSintetico()
        self._azar = random.Random(self.config.semilla)
        self._catalogo = CatalogoMexicano(self._azar)
        self._renderizador = RenderizadorTicket(self.config)
        self._degradaciones = [
            TintaTermica(self._azar), SombraDespareja(self._azar),
            DesenfoqueDeCamara(self._azar), PerspectivaDeMesa(self._azar),
            RuidoDeSensor(self._azar), CompresionJPEG(self._azar),
        ]
        from divieat_ticket.plantillas import CatalogoDePlantillas

        self._plantillas = CatalogoDePlantillas(self._azar)

    def ticket(self) -> tuple[TicketExtraido, "ContextoDeTicket"]:
        """Construye la verdad de referencia y el contexto que la rodea.

        La aritmetica fiscal es la de los tickets reales: los precios de carta
        ya incluyen IVA, asi que **la suma de los renglones es el TOTAL** y el
        subtotal es la base gravable (total / 1.16). Lo contrario —subtotal
        como suma de productos— fue el error que corrigieron los tickets de
        Merida.
        """
        from divieat_ticket.plantillas import ContextoDeTicket

        nombre, direccion = self._catalogo.restaurante()
        cuantos = self._azar.randint(self.config.productos_min, self.config.productos_max)
        productos = []
        for indice, (descripcion, unitario) in enumerate(self._catalogo.muestra(cuantos)):
            cantidad = self._azar.choices([1, 2, 3, 4], weights=[6, 3, 2, 1])[0]
            productos.append(
                Producto(
                    descripcion=descripcion,
                    cantidad=cantidad,
                    importe=Dinero(unitario * cantidad),
                    precio_unitario=Dinero(unitario),
                    linea=indice,
                )
            )
        total = Dinero.suma(p.importe for p in productos)
        base = Dinero(int(round(total.centavos / 1.16)))
        apertura = datetime(2026, 1, 1, 12, 0) + timedelta(
            days=self._azar.randrange(330), minutes=self._azar.randrange(700)
        )
        folio = str(self._azar.randrange(1000, 999999))

        ticket = TicketExtraido(
            productos=productos,
            restaurante=nombre,
            fecha=apertura,
            folio=folio,
            subtotal=base,
            iva=total - base,
            total_impreso=total,
        )
        contexto = ContextoDeTicket(
            nombre=nombre,
            direccion=direccion,
            razon_social=self._azar.choice(CatalogoMexicano.RAZONES),
            rfc=self._rfc(),
            telefono=str(self._azar.randrange(9_000_000_000, 9_999_999_999)),
            sucursal=direccion if self._azar.random() < 0.6 else "",
            mesa=self._azar.choice(["2Y7", "SALA4", "33", "56", "A12", "7", "42"]),
            mesero=self._azar.choice(CatalogoMexicano.MESEROS),
            cajero="" if self._azar.random() < 0.7 else self._azar.choice(CatalogoMexicano.MESEROS),
            comensales=self._azar.randint(1, 8),
            orden=self._azar.randrange(1, 300),
            apertura=apertura,
            cierre=apertura + timedelta(minutes=self._azar.randrange(20, 120)),
            version_pos=self._azar.choice(["10", "11", "12"]),
            codigo_factura=f"{self._azar.randrange(10000, 99999)}LARAXGLF",
            dias_vigencia=self._azar.choice(["7", "30", "ULTIMO DIA DEL MES"]),
            sitio_factura=f"https://mefacturo.mx/{nombre.split()[-1].lower()}",
        )
        return ticket, contexto

    def _rfc(self) -> str:
        letras = "".join(self._azar.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(3))
        return f"{letras}{self._azar.randrange(100000, 999999)}{self._azar.choice('ABCDEFGHJKLMNP')}{self._azar.randrange(10, 99)}"

    def generar(self, degradar: bool = True) -> MuestraSintetica:
        ticket, contexto = self.ticket()
        estilo = EstiloDeImporte.elegir(self._azar)
        plantilla = self._plantillas.elegir()
        renglones = self._renderizador.lineas_de_texto(ticket, contexto, estilo, plantilla)
        lienzo, cajas = self._renderizador.renderizar_con_cajas(ticket, contexto, estilo, plantilla)
        papel = np.array(lienzo)
        limpia = Imagen(papel.copy())
        mascara = mascara_de_renglones(papel.shape, cajas)

        aplicadas: list[str] = []
        matriz = papel
        if degradar:
            for degradacion in self._degradaciones:
                if self._azar.random() < 0.75:
                    matriz, mascara = degradacion.aplicar(matriz, mascara)
                    aplicadas.append(degradacion.nombre)
        return MuestraSintetica(Imagen(matriz), ticket, limpia, aplicadas, renglones, mascara)

    def lote(self, cantidad: int, degradar: bool = True) -> list[MuestraSintetica]:
        return [self.generar(degradar) for _ in range(cantidad)]


def mascara_de_renglones(
    forma: tuple[int, int], cajas: list[tuple[int, int, int, int]], encogimiento: float = 0.5
) -> np.ndarray:
    """Pinta el nucleo de cada renglon, encogido verticalmente.

    El encogimiento es lo que hace util la mascara: dos renglones contiguos
    nunca se tocan, asi que sus componentes conexas salen separadas sin
    importar cuan juntos esten. Y como la banda va de extremo a extremo del
    renglon, la descripcion y su importe caen en la misma componente aunque
    medien 600 px de hueco.
    """
    mascara = np.zeros(forma, np.uint8)
    for x, y, ancho, alto in cajas:
        margen = int(alto * (1 - encogimiento) / 2)
        y0, y1 = y + margen, y + alto - margen
        if y1 <= y0:
            y0, y1 = y, y + max(1, alto)
        mascara[max(0, y0): y1, max(0, x): x + ancho] = 255
    return mascara
