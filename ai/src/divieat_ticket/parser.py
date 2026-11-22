"""De lineas de OCR a productos estructurados.

Dos ideas sostienen este modulo:

1. **Normalizacion por contexto.** El OCR confunde caracteres segun donde
   esten: en un numero lee `S` donde hay 5, y en una palabra lee 0 donde hay O.
   `NormalizadorOCR` decide por token cual de las dos direcciones aplicar; sin
   eso, «T0TAL l,6SO.0O» no se parsea.
2. **Estructura antes que heuristica.** Si reconocemos la plantilla del POS
   (`perfiles.py`), los productos son los renglones entre el encabezado de
   tabla y el TOTAL. Eso es mucho mas fiable que mirar cada linea por separado.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Sequence

from divieat_ticket.dominio import Dinero, Producto, TicketExtraido
from divieat_ticket.ocr import LineaOCR, ResultadoOCR
from divieat_ticket.perfiles import BloqueDeProductos, DetectorDePerfil, PerfilDeTicket


class TipoLinea(Enum):
    ENCABEZADO = "encabezado"
    ENCABEZADO_TABLA = "enc-tabla"
    METADATO = "metadato"
    FECHA = "fecha"
    PRODUCTO = "producto"
    UNITARIO = "unitario"
    SUBTOTAL = "subtotal"
    IMPUESTO = "impuesto"
    PROPINA = "propina"
    TOTAL = "total"
    SEPARADOR = "separador"
    NOTA = "nota"
    RUIDO = "ruido"


@dataclass(frozen=True)
class LineaClasificada:
    linea: LineaOCR
    tipo: TipoLinea
    texto_normalizado: str

    @property
    def confianza(self) -> float:
        return self.linea.confianza

    def __str__(self) -> str:
        return f"{self.tipo.value:<10} | {self.texto_normalizado}"


class NormalizadorOCR:
    """Corrige confusiones de caracteres segun el token sea numero o palabra."""

    _LETRA_A_DIGITO = str.maketrans({"O": "0", "o": "0", "D": "0", "l": "1", "I": "1",
                                     "|": "1", "i": "1", "S": "5", "s": "5", "B": "8",
                                     "Z": "2", "z": "2", "g": "9", "q": "9"})
    _DIGITO_A_LETRA = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"})
    _SOLO_NUMERO = re.compile(r"^[\$]?[\d.,]+$")

    def normalizar(self, texto: str) -> str:
        return " ".join(self._token(t, i) for i, t in enumerate(texto.split()))

    def _token(self, token: str, posicion: int) -> str:
        if posicion == 0 and token in {"l", "I", "|", "i"}:
            return "1"  # cantidad al inicio del renglon
        if ":" in token:
            # clave:valor del POS (MESA:2Y7, FOLIO:122903). El valor es un
            # identificador, no prosa: "corregirlo" lo destruye.
            return token
        if self._parece_numero(token):
            candidato = token.translate(self._LETRA_A_DIGITO)
            return candidato if self._SOLO_NUMERO.match(candidato) else token
        if any(c.isdigit() for c in token) and sum(c.isalpha() for c in token) >= 3:
            return token.translate(self._DIGITO_A_LETRA)
        return token

    @staticmethod
    def _parece_numero(token: str) -> bool:
        limpio = token.strip("$@()")
        if not limpio:
            return False
        digitos = sum(c.isdigit() for c in limpio)
        if digitos == 0:
            return False
        if "," in limpio or "." in limpio:
            return True
        letras = sum(c.isalpha() for c in limpio)
        return digitos >= letras


class ClasificadorDeLineas(ABC):
    """Decide que es cada renglon del ticket."""

    @abstractmethod
    def clasificar(self, texto: str) -> TipoLinea:
        ...

    @property
    def nombre(self) -> str:
        return type(self).__name__


class ClasificadorHeuristico(ClasificadorDeLineas):
    """Reglas explicitas, ordenadas de mas especifica a mas general.

    Es la linea base contra la que se mide cualquier modelo entrenado.
    """

    _SEPARADOR = re.compile(r"^[-=_*~.\s]{6,}$")
    _ENC_TABLA = re.compile(r"CANT\.?\s*DESCRIPCION", re.IGNORECASE)
    _METADATO = re.compile(
        r"^\s*(MESA|MESERO|PERSONAS|ORDEN|FOLIO|CAJERO|CLIENTE|TURNO|CAJA|RFC|TEL|SUCURSAL"
        r"|CODIGO\s+FACT|DIAS\s+VIGENCIA)\b",
        re.IGNORECASE,
    )
    _DIRECCION = re.compile(r"\bC\.?P\.?\s*\d{5}\b", re.IGNORECASE)
    _SUBTOTAL = re.compile(r"\bSUB\s*-?\s*TOTAL\b", re.IGNORECASE)
    _IMPUESTO = re.compile(r"\b(IVA|I\.V\.A|IEPS|IMPUESTOS?)\b", re.IGNORECASE)
    _PROPINA = re.compile(r"\b(PROPINA|TIP|SERVICIO)\b", re.IGNORECASE)
    _SIN_PROPINA = re.compile(r"\bNO\s+(INCLUID|INCLUDED)", re.IGNORECASE)
    _TOTAL = re.compile(r"\bTOTAL\b", re.IGNORECASE)
    _UNITARIO = re.compile(r"^\s*[@]|\bC\s*/\s*U\b", re.IGNORECASE)
    _FECHA = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")
    _NOTA = re.compile(
        r"^\s*SON\s*:|COMPROBANTE\s+FISCAL|https?://|GRACIAS|FACTURA|VIGENCIA|@\w+\.\w+",
        re.IGNORECASE,
    )
    _IMPORTE_FINAL = re.compile(r"[\d.,]{2,}\s*$")

    def clasificar(self, texto: str) -> TipoLinea:
        limpio = texto.strip()
        if not limpio:
            return TipoLinea.RUIDO
        if self._SEPARADOR.match(limpio):
            return TipoLinea.SEPARADOR
        if self._ENC_TABLA.search(limpio):
            return TipoLinea.ENCABEZADO_TABLA
        if self._METADATO.match(limpio):
            return TipoLinea.METADATO
        if self._DIRECCION.search(limpio):
            return TipoLinea.ENCABEZADO
        if self._SUBTOTAL.search(limpio):
            return TipoLinea.SUBTOTAL
        if self._PROPINA.search(limpio):
            return TipoLinea.NOTA if self._SIN_PROPINA.search(limpio) else TipoLinea.PROPINA
        if self._IMPUESTO.search(limpio):
            return TipoLinea.IMPUESTO
        if self._TOTAL.search(limpio):
            return TipoLinea.TOTAL
        if self._UNITARIO.search(limpio):
            return TipoLinea.UNITARIO
        if self._NOTA.search(limpio):
            return TipoLinea.NOTA
        if self._FECHA.search(limpio):
            return TipoLinea.FECHA
        if self._IMPORTE_FINAL.search(limpio) and sum(c.isalpha() for c in limpio) >= 3:
            return TipoLinea.PRODUCTO
        return TipoLinea.ENCABEZADO if limpio.isupper() else TipoLinea.RUIDO


class ExtractorDeProductos:
    """Convierte un renglon en `Producto`. No decide si el renglon lo es."""

    _PRODUCTO = re.compile(
        r"""^\s*
        (?:(?P<cantidad>\d{1,3})\s+)?
        (?P<descripcion>.*?[A-Za-zÁÉÍÓÚÑáéíóúñ].*?)
        \s+\$?\s*(?P<importe>\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2})?)
        \s*$""",
        re.VERBOSE,
    )
    _UNITARIO = re.compile(r"[@xX]\s*\$?\s*(?P<valor>[\d.,]+)")

    def extraer(self, texto: str, confianza: float, indice: int) -> Producto | None:
        coincidencia = self._PRODUCTO.match(texto)
        if coincidencia is None:
            return None
        importe = Dinero.desde_texto(coincidencia.group("importe"))
        if importe is None or importe.centavos <= 0:
            return None
        descripcion = coincidencia.group("descripcion").strip(" .-:$")
        if len(descripcion) < 3 or not any(c.isalpha() for c in descripcion):
            return None
        cantidad = int(coincidencia.group("cantidad") or 1)
        if cantidad < 1 or cantidad > 99:
            return None
        return Producto(
            descripcion=descripcion,
            cantidad=cantidad,
            importe=importe,
            confianza=confianza,
            linea=indice,
        )

    def unitario(self, texto: str) -> Dinero | None:
        coincidencia = self._UNITARIO.search(texto)
        return Dinero.desde_texto(coincidencia.group("valor")) if coincidencia else None


class LectorDeMetadatos:
    """Saca mesa, comensales, folio y fecha del bloque de cabecera."""

    _MESA = re.compile(r"\bMESA\s*[:.]?\s*(?P<valor>[A-Z0-9][A-Z0-9-]{0,9})", re.IGNORECASE)
    _PERSONAS = re.compile(r"\bPERSONAS\s*[:.]?\s*(?P<valor>\d{1,2})", re.IGNORECASE)
    _FOLIO = re.compile(
        r"\bFOLIO\s*(?:NO\.?|N[°º]|#)?\s*[:.]?\s*(?P<valor>[A-Z0-9][A-Z0-9-]{2,})",
        re.IGNORECASE,
    )
    _FECHA = re.compile(r"(?P<dia>\d{1,2})[/-](?P<mes>\d{1,2})[/-](?P<anio>\d{2,4})")
    _HORA = re.compile(
        r"(?P<hora>\d{1,2}):(?P<minuto>\d{2})(?::(?P<segundo>\d{2}))?\s*(?P<meridiano>[AP]\.?\s?M\.?)?",
        re.IGNORECASE,
    )

    def mesa(self, texto: str) -> str | None:
        c = self._MESA.search(texto)
        return c.group("valor") if c else None

    def comensales(self, texto: str) -> int | None:
        c = self._PERSONAS.search(texto)
        return int(c.group("valor")) if c else None

    def folio(self, texto: str) -> str | None:
        c = self._FOLIO.search(texto)
        return c.group("valor") if c else None

    def fecha(self, texto: str) -> datetime | None:
        """Lee fecha y hora, resolviendo el formato de 12 horas con AM/PM."""
        fecha = self._FECHA.search(texto)
        if fecha is None:
            return None
        anio = int(fecha.group("anio"))
        if anio < 100:
            anio += 2000

        hora = minuto = 0
        reloj = self._HORA.search(texto, fecha.end())
        if reloj is not None:
            hora, minuto = int(reloj.group("hora")), int(reloj.group("minuto"))
            meridiano = (reloj.group("meridiano") or "").upper().replace(".", "").replace(" ", "")
            if meridiano == "PM" and hora < 12:
                hora += 12
            elif meridiano == "AM" and hora == 12:
                hora = 0
        try:
            return datetime(anio, int(fecha.group("mes")), int(fecha.group("dia")), hora, minuto)
        except ValueError:
            return None


class AnalizadorDeTicket:
    """Orquesta normalizacion, deteccion de plantilla, clasificacion y extraccion."""

    def __init__(
        self,
        clasificador: ClasificadorDeLineas | None = None,
        normalizador: NormalizadorOCR | None = None,
        extractor: ExtractorDeProductos | None = None,
        detector: DetectorDePerfil | None = None,
    ) -> None:
        self.clasificador = clasificador or ClasificadorHeuristico()
        self.normalizador = normalizador or NormalizadorOCR()
        self.extractor = extractor or ExtractorDeProductos()
        self.detector = detector or DetectorDePerfil()
        self.corrector = CorrectorDeImportes()
        self.metadatos = LectorDeMetadatos()
        self.ultimo_perfil: PerfilDeTicket | None = None
        self.ultimo_puntaje: float = 0.0
        self.ultimo_bloque: BloqueDeProductos | None = None

    # ------------------------------------------------------------------ pasos
    def clasificar(self, resultado: ResultadoOCR) -> list[LineaClasificada]:
        normalizadas = [self.normalizador.normalizar(l.texto) for l in resultado]
        self.ultimo_perfil, self.ultimo_puntaje = self.detector.detectar(normalizadas)
        self.ultimo_bloque = self.ultimo_perfil.localizar_productos(normalizadas)

        clasificadas: list[LineaClasificada] = []
        for indice, (linea, texto) in enumerate(zip(resultado, normalizadas)):
            tipo = self.clasificador.clasificar(texto)
            tipo = self._ajustar_por_estructura(tipo, indice, texto)
            clasificadas.append(LineaClasificada(linea, tipo, texto))
        return clasificadas

    def _ajustar_por_estructura(self, tipo: TipoLinea, indice: int, texto: str) -> TipoLinea:
        """La plantilla manda sobre la heuristica cuando sabemos donde empieza
        y termina el consumo: fuera del bloque nada puede ser producto."""
        if self.ultimo_bloque is None:
            return tipo
        dentro = self.ultimo_bloque.contiene(indice)
        if dentro and tipo in {TipoLinea.ENCABEZADO, TipoLinea.RUIDO, TipoLinea.METADATO}:
            if self.extractor.extraer(texto, 1.0, indice) is not None:
                return TipoLinea.PRODUCTO
        if not dentro and tipo is TipoLinea.PRODUCTO:
            return TipoLinea.ENCABEZADO
        return tipo

    def analizar(self, resultado: ResultadoOCR) -> TicketExtraido:
        clasificadas = self.clasificar(resultado)
        ticket = TicketExtraido(motor_ocr=resultado.motor)
        ticket.perfil_pos = self.ultimo_perfil.nombre if self.ultimo_perfil else None

        for posicion, item in enumerate(clasificadas):
            texto = item.texto_normalizado
            tipo = item.tipo

            if tipo is TipoLinea.PRODUCTO:
                producto = self.extractor.extraer(texto, item.confianza, item.linea.indice)
                if producto is not None:
                    self._aplicar_unitario_siguiente(producto, clasificadas, posicion)
                    ticket.productos.append(producto)
            elif tipo is TipoLinea.SUBTOTAL:
                self._leer_subtotal_e_iva(ticket, texto)
            elif tipo is TipoLinea.IMPUESTO:
                ticket.iva = Dinero.desde_texto(texto) or ticket.iva
            elif tipo is TipoLinea.PROPINA:
                ticket.propina = Dinero.desde_texto(texto) or ticket.propina
            elif tipo is TipoLinea.TOTAL:
                ticket.total_impreso = Dinero.desde_texto(texto) or ticket.total_impreso
            elif tipo is TipoLinea.FECHA:
                ticket.fecha = self.metadatos.fecha(texto) or ticket.fecha
            elif tipo is TipoLinea.METADATO:
                self._leer_metadato(ticket, texto)
            elif tipo is TipoLinea.ENCABEZADO and ticket.restaurante is None:
                ticket.restaurante = texto.strip()

        # El papel se verifica a si mismo: subtotal + IVA fija el total, y el
        # total fija los importes. Se aplica al final, con el ticket completo.
        self.corrector.corregir_total(ticket)
        self.corrector.corregir(ticket)
        return ticket

    # ------------------------------------------------------------- auxiliares
    def _leer_subtotal_e_iva(self, ticket: TicketExtraido, texto: str) -> None:
        """«SUBTOTAL:$1,012.93  IVA:$162.07» viene en un solo renglon."""
        partes = re.split(r"\bIVA\b\s*:?", texto, maxsplit=1, flags=re.IGNORECASE)
        ticket.subtotal = Dinero.desde_texto(partes[0]) or ticket.subtotal
        if len(partes) > 1:
            ticket.iva = Dinero.desde_texto(partes[1]) or ticket.iva

    def _leer_metadato(self, ticket: TicketExtraido, texto: str) -> None:
        ticket.mesa = ticket.mesa or self.metadatos.mesa(texto)
        ticket.comensales = ticket.comensales or self.metadatos.comensales(texto)
        ticket.folio = ticket.folio or self.metadatos.folio(texto)
        if ticket.fecha is None:
            ticket.fecha = self.metadatos.fecha(texto)

    def _aplicar_unitario_siguiente(
        self, producto: Producto, clasificadas: Sequence[LineaClasificada], posicion: int
    ) -> None:
        """El renglon «@ 55.00 c/u» confirma el unitario del producto anterior."""
        if posicion + 1 >= len(clasificadas):
            return
        siguiente = clasificadas[posicion + 1]
        if siguiente.tipo is not TipoLinea.UNITARIO:
            return
        unitario = self.extractor.unitario(siguiente.texto_normalizado)
        if unitario is not None and unitario.centavos > 0:
            producto.precio_unitario = unitario


class CorrectorDeImportes:
    """Usa el TOTAL impreso como suma de verificacion para reparar importes.

    El OCR confunde el simbolo de moneda con un digito: `$160.00` se lee
    `8160,00` y `$1,175.00` se lee `51,175`. El error es sistematico y, visto
    en aislamiento, indistinguible de un importe legitimo.

    Pero el ticket trae su propia verificacion: la suma de los renglones tiene
    que dar el TOTAL. Si no cuadra, se buscan las correcciones que la cuadran.
    Solo se aplican si existe **una** combinacion que encaja exactamente; con
    varias candidatas, adivinar seria peor que dejar el dato dudoso.
    """

    CONFUNDIBLES_CON_MONEDA = "58S$"

    def __init__(self, tolerancia: Dinero | None = None, maximo_productos: int = 24) -> None:
        self.tolerancia = tolerancia or Dinero(100)
        self.maximo_productos = maximo_productos

    def candidatos(self, importe: Dinero) -> list[Dinero]:
        """Lecturas alternativas de un importe, la original primero."""
        opciones = [importe]
        entero, centavos = divmod(abs(importe.centavos), 100)
        texto = str(entero)
        if len(texto) > 1 and texto[0] in "58":
            recortado = texto[1:].lstrip("0") or "0"
            alternativa = Dinero(int(recortado) * 100 + centavos)
            if alternativa.centavos > 0 and alternativa != importe:
                opciones.append(alternativa)
        return opciones

    def corregir_total(self, ticket: TicketExtraido) -> bool:
        """Repara el TOTAL usando la otra verificacion del papel: subtotal + IVA.

        El simbolo de moneda del TOTAL tambien se confunde (`$1,175.00` ->
        `51,175`). Cuando el ticket trae subtotal e IVA, su suma es la base mas
        fiable para elegir entre las lecturas posibles del total.
        """
        if ticket.subtotal is None or ticket.iva is None:
            return False
        esperado = ticket.subtotal + ticket.iva
        if ticket.total_impreso is not None:
            if abs(ticket.total_impreso - esperado).centavos <= self.tolerancia.centavos:
                return False
            for candidato in self.candidatos(ticket.total_impreso):
                if abs(candidato - esperado).centavos <= self.tolerancia.centavos:
                    ticket.total_impreso = candidato
                    return True
            # Ninguna lectura del total coincide con subtotal + IVA: entonces
            # el mal leido pudo ser cualquiera de los tres. Sustituir uno por
            # otro seria cambiar un dato dudoso por otro igual de dudoso.
            return False
        ticket.total_impreso = esperado
        return True

    def corregir(self, ticket: TicketExtraido) -> int:
        """Ajusta los importes para que cuadren. Devuelve cuantos cambio."""
        objetivo = ticket.total_de_referencia
        if objetivo is None or not ticket.productos:
            return 0
        if ticket.cuadra(self.tolerancia):
            return 0
        if len(ticket.productos) > self.maximo_productos:
            return 0

        eleccion = self._buscar_combinacion(ticket.productos, objetivo)
        if eleccion is None:
            return 0

        cambiados = 0
        for producto, importe in zip(ticket.productos, eleccion):
            if importe != producto.importe:
                producto.importe = importe
                producto.precio_unitario = (
                    Dinero(importe.centavos // producto.cantidad)
                    if importe.centavos % producto.cantidad == 0
                    else None
                )
                # Se corrigio por cuadre, no porque se leyera bien: queda marcado
                # para que la pantalla de revision lo resalte.
                producto.confianza = min(producto.confianza, 0.6)
                cambiados += 1
        return cambiados

    def _buscar_combinacion(
        self, productos: list[Producto], objetivo: Dinero
    ) -> list[Dinero] | None:
        """Programacion dinamica sobre las sumas alcanzables.

        Se exige solucion unica: si dos combinaciones distintas dan el total,
        no hay forma de saber cual leyo mal el OCR.
        """
        limite = objetivo.centavos + self.tolerancia.centavos
        alcanzables: dict[int, list[Dinero] | None] = {0: []}   # None = ambigua
        for producto in productos:
            siguiente: dict[int, list[Dinero] | None] = {}
            for suma, camino in alcanzables.items():
                for candidato in self.candidatos(producto.importe):
                    total = suma + candidato.centavos
                    if total > limite:
                        continue
                    if total in siguiente:
                        siguiente[total] = None          # dos caminos: ambiguo
                    elif camino is None:
                        siguiente[total] = None
                    else:
                        siguiente[total] = camino + [candidato]
            alcanzables = siguiente
            if not alcanzables:
                return None

        mejor = None
        for suma, camino in alcanzables.items():
            if abs(suma - objetivo.centavos) <= self.tolerancia.centavos:
                if camino is None or mejor is not None:
                    return None                           # ambiguo
                mejor = camino
        return mejor
