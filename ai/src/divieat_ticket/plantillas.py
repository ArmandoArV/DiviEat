"""Plantillas de impresion de ticket.

`perfiles.py` reconoce la plantilla de un POS; este modulo la **imprime**. Son
las dos caras de lo mismo, y tienen que estar alineadas: mientras el generador
produjo tickets genericos, la evaluacion detectaba `PerfilGenerico` en 8 de 8
casos y la ruta estructural del parser —la unica validada contra tickets
reales— nunca se ejercitaba.

La plantilla dominante es la de **SOFT RESTAURANT**, el POS mas extendido en
restaurantes mexicanos. Todo lo que aparece aqui esta copiado de tickets
reales de Merida y Cuernavaca: el bloque `MESA:`/`MESERO:`/`FOLIO:`, las dos
marcas de tiempo con AM/PM, el encabezado `CANT. DESCRIPCION ... IMPORTE`, el
importe en letras, `SUBTOTAL:$x IVA:$y` en un solo renglon y el pie
`***SOFT RESTAURANT V12 PRO***`.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Sequence

from divieat_ticket.dominio import Dinero, TicketExtraido

Renglon = tuple[str, bool, bool]       # (texto, centrado, es_titulo)


class NumeroEnLetras:
    """Convierte un importe a la frase que imprime el POS.

    Los tickets escriben «SON:UN MIL CIENTO SETENTA Y CINCO PESOS 00/100 M.N.»;
    nota el «UN MIL», no «MIL», que es como lo imprime SOFT RESTAURANT.
    """

    UNIDADES = ("", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
                "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS",
                "DIECISIETE", "DIECIOCHO", "DIECINUEVE", "VEINTE")
    VEINTIS = ("VEINTIUNO", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO",
               "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE")
    DECENAS = ("", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA",
               "OCHENTA", "NOVENTA")
    CENTENAS = ("", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS")

    def convertir(self, importe: Dinero) -> str:
        entero, centavos = divmod(abs(importe.centavos), 100)
        return f"{self._entero(entero)} PESOS {centavos:02d}/100 M.N."

    def _entero(self, numero: int) -> str:
        if numero == 0:
            return "CERO"
        if numero >= 1_000_000:
            return str(numero)                     # fuera del rango de un ticket
        partes = []
        miles, resto = divmod(numero, 1000)
        if miles == 1:
            partes.append("UN MIL")
        elif miles > 1:
            partes.append(f"{self._centenas(miles)} MIL")
        if resto:
            partes.append(self._centenas(resto))
        return " ".join(partes)

    def _centenas(self, numero: int) -> str:
        if numero == 100:
            return "CIEN"
        centenas, resto = divmod(numero, 100)
        partes = []
        if centenas:
            partes.append(self.CENTENAS[centenas])
        if resto:
            partes.append(self._decenas(resto))
        return " ".join(partes)

    def _decenas(self, numero: int) -> str:
        if numero <= 20:
            return self.UNIDADES[numero]
        if numero < 30:
            return self.VEINTIS[numero - 21]
        decenas, unidades = divmod(numero, 10)
        if unidades == 0:
            return self.DECENAS[decenas]
        return f"{self.DECENAS[decenas]} Y {self.UNIDADES[unidades]}"


@dataclass
class ContextoDeTicket:
    """Los datos que rodean al consumo y que el POS imprime alrededor."""

    nombre: str
    direccion: str
    razon_social: str = ""
    rfc: str = ""
    telefono: str = ""
    sucursal: str = ""
    mesa: str = "1"
    mesero: str = ""
    cajero: str = ""
    comensales: int = 2
    orden: int = 1
    apertura: datetime | None = None
    cierre: datetime | None = None
    version_pos: str = "12"
    codigo_factura: str = ""
    dias_vigencia: str = "7"
    sitio_factura: str = "https://mefacturo.mx/restaurante"


class PlantillaTicket(ABC):
    """Compone los renglones que se van a imprimir."""

    @property
    def nombre(self) -> str:
        return type(self).__name__

    @abstractmethod
    def componer(
        self, ticket: TicketExtraido, contexto: ContextoDeTicket, estilo, ancho: int
    ) -> list[Renglon]:
        ...

    # ------------------------------------------------------------ utilidades
    @staticmethod
    def _dos_columnas(izquierda: str, derecha: str, ancho: int) -> str:
        espacio = max(1, ancho - len(izquierda) - len(derecha))
        return f"{izquierda}{' ' * espacio}{derecha}"

    @staticmethod
    def _partir_duro(texto: str, ancho: int) -> list[str]:
        """Parte cada `ancho` caracteres, sin respetar palabras.

        Los tickets reales cortan a mitad de palabra: «... COLONI» / «A VISTA
        HERMOSA ...». Imitarlo importa porque el parser tiene que sobrevivir a
        renglones que no son frases completas.
        """
        texto = texto.strip()
        if not texto:
            return []
        return [texto[i: i + ancho] for i in range(0, len(texto), ancho)] or [texto]


class PlantillaSoftRestaurant(PlantillaTicket):
    """La plantilla del POS mas comun en Mexico (v10 a v12 PRO)."""

    def __init__(self, azar: random.Random) -> None:
        self._azar = azar
        self._letras = NumeroEnLetras()

    def componer(self, ticket, contexto, estilo, ancho: int) -> list[Renglon]:
        renglones: list[Renglon] = [(contexto.nombre, True, True)]
        if contexto.razon_social:
            renglones.append((contexto.razon_social, True, False))
        if contexto.rfc:
            renglones.append((f"RFC:{contexto.rfc}", True, False))
        renglones += [(parte, True, False) for parte in self._partir_duro(contexto.direccion, ancho)]
        renglones.append(("LUGAR DE EXPEDICION", True, False))
        if contexto.sucursal:
            renglones += [(p, True, False) for p in self._partir_duro(contexto.sucursal, ancho)]
        if contexto.telefono:
            renglones.append((f"TEL:{contexto.telefono}", True, False))

        renglones.append(("=" * ancho, False, False))
        renglones.append((f"MESA:{contexto.mesa}", False, False))
        renglones.append((f"MESERO:{contexto.mesero}", False, False))
        renglones.append((
            self._dos_columnas(
                f"PERSONAS:{contexto.comensales}", f"ORDEN:{contexto.orden}", int(ancho * 0.65)
            ), False, False,
        ))
        if ticket.folio:
            renglones.append((f"FOLIO:{ticket.folio}", False, False))
        for marca in (contexto.apertura, contexto.cierre):
            if marca is not None:
                renglones.append((self._marca_de_tiempo(marca), False, False))
        renglones.append((f"CAJERO:{contexto.cajero}", False, False))

        renglones.append(("-" * ancho, False, False))
        renglones.append((self._dos_columnas("CANT. DESCRIPCION", "IMPORTE", ancho), False, False))
        for producto in ticket.productos:
            etiqueta = f"{producto.cantidad}     {producto.descripcion}"
            renglones.append((
                self._dos_columnas(etiqueta, estilo.formatear(producto.importe), ancho),
                False, False,
            ))
        renglones.append(("-" * ancho, False, False))

        if ticket.total_impreso:
            renglones.append((
                self._dos_columnas("TOTAL:", estilo.formatear(ticket.total_impreso),
                                   int(ancho * 0.8)),
                False, False,
            ))
        renglones.append(("=" * ancho, False, False))

        if ticket.total_impreso:
            # El POS corta la frase en seco; por eso el «.N.» cae solo abajo.
            frase = f"SON:{self._letras.convertir(ticket.total_impreso)}"
            renglones += [(p, False, False) for p in self._partir_duro(frase, ancho)]
        if ticket.subtotal and ticket.iva:
            renglones.append((
                f"SUBTOTAL:{ticket.subtotal}   IVA:{ticket.iva}".replace(",", ","),
                False, False,
            ))
        if ticket.propina is None and self._azar.random() < 0.5:
            renglones.append(("PROPINA NO INCLUIDA", False, False))
        renglones.append(("ESTE NO ES UN COMPROBANTE FISCAL", True, False))

        renglones.append(("=" * ancho, False, False))
        renglones += [
            ("Si requiere factura, escanee el codigo QR o", True, False),
            ("ingrese a la siguiente pagina", True, False),
            (contexto.sitio_factura, True, False),
            (f"CODIGO FACT: {contexto.codigo_factura}", True, False),
        ]
        if ticket.folio:
            renglones.append((f"FOLIO: {ticket.folio}", True, False))
        renglones += [
            (f"DIAS VIGENCIA: {contexto.dias_vigencia}", True, False),
            (f"***SOFT RESTAURANT V{contexto.version_pos} PRO***", True, False),
        ]
        return renglones

    @staticmethod
    def _marca_de_tiempo(momento: datetime) -> str:
        meridiano = "AM" if momento.hour < 12 else "PM"
        hora = momento.hour % 12 or 12
        return f"{momento:%d/%m/%Y} {hora:02d}:{momento:%M:%S} {meridiano}"


class PlantillaGenerica(PlantillaTicket):
    """Ticket simple, sin plantilla de POS reconocible.

    Se conserva para que el sistema no asuma que todo el mundo usa SOFT
    RESTAURANT: hay cajas que imprimen formatos propios.
    """

    def componer(self, ticket, contexto, estilo, ancho: int) -> list[Renglon]:
        renglones: list[Renglon] = [
            (contexto.nombre, True, True),
            (contexto.direccion, True, False),
            ("", False, False),
        ]
        if contexto.cierre:
            renglones.append((f"{contexto.cierre:%d/%m/%Y %H:%M}", False, False))
        if ticket.folio:
            renglones.append((f"FOLIO {ticket.folio}", False, False))
        renglones.append(("-" * ancho, False, False))

        for producto in ticket.productos:
            unitario = producto.precio_unitario or producto.importe
            renglones.append((
                self._dos_columnas(f"{producto.cantidad} {producto.descripcion}",
                                   estilo.formatear(producto.importe), ancho),
                False, False,
            ))
            if producto.cantidad > 1:
                renglones.append((f"    @ {estilo.formatear(unitario).strip()} c/u", False, False))

        renglones.append(("-" * ancho, False, False))
        for etiqueta, importe in (("SUBTOTAL", ticket.subtotal), ("PROPINA SUGERIDA", ticket.propina),
                                  ("TOTAL", ticket.total_impreso)):
            if importe:
                renglones.append((self._dos_columnas(etiqueta, estilo.formatear(importe), ancho),
                                  False, False))
        renglones += [("", False, False), ("GRACIAS POR SU VISITA", True, False)]
        return renglones


class CatalogoDePlantillas:
    """Elige plantilla con la frecuencia aproximada del mercado mexicano."""

    def __init__(self, azar: random.Random, peso_soft: float = 0.75) -> None:
        self._azar = azar
        self.peso_soft = peso_soft
        self._soft = PlantillaSoftRestaurant(azar)
        self._generica = PlantillaGenerica()

    def elegir(self) -> PlantillaTicket:
        return self._soft if self._azar.random() < self.peso_soft else self._generica

    @property
    def plantillas(self) -> Sequence[PlantillaTicket]:
        return (self._soft, self._generica)
