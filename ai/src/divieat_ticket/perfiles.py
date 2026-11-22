"""Perfiles de punto de venta.

Los tickets no son texto libre: los imprime un POS con plantilla fija. En
Mexico **SOFT RESTAURANT** es el mas extendido, asi que conviene reconocer su
plantilla y usar su *estructura* en vez de adivinar renglon por renglon: el
bloque de productos vive entre el encabezado «CANT. DESCRIPCION ... IMPORTE»
y la linea «TOTAL:». Esa sola regla elimina los falsos positivos que generan
las lineas de direccion («... CP 97302») o de mesa («MESA:2Y7»).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BloqueDeProductos:
    """Rango [inicio, fin) de renglones que contienen consumo."""

    inicio: int
    fin: int

    def contiene(self, indice: int) -> bool:
        return self.inicio <= indice < self.fin

    def __len__(self) -> int:
        return max(0, self.fin - self.inicio)


class PerfilDeTicket(ABC):
    """Conocimiento de una plantilla concreta de POS."""

    @property
    def nombre(self) -> str:
        return type(self).__name__

    @abstractmethod
    def puntaje(self, lineas: Sequence[str]) -> float:
        """Que tan seguro estoy de que el ticket es de este POS (0..1)."""

    @abstractmethod
    def localizar_productos(self, lineas: Sequence[str]) -> BloqueDeProductos | None:
        """Rango estructural de productos, o None si hay que caer a heuristica."""

    def __repr__(self) -> str:
        return f"<{self.nombre}>"


class PerfilSoftRestaurant(PerfilDeTicket):
    """SOFT RESTAURANT (v11/v12 PRO): el POS mas comun en restaurantes mexicanos."""

    HUELLAS: tuple[re.Pattern[str], ...] = (
        re.compile(r"SOFT\s*RESTAURANT", re.IGNORECASE),
        re.compile(r"^\s*MESA\s*:", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^\s*MESERO\s*:", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^\s*FOLIO\s*:", re.IGNORECASE | re.MULTILINE),
        re.compile(r"CANT\.?\s*DESCRIPCION", re.IGNORECASE),
        re.compile(r"^\s*SON\s*:", re.IGNORECASE | re.MULTILINE),
        re.compile(r"CODIGO\s+FACT", re.IGNORECASE),
        re.compile(r"LUGAR\s+DE\s+EXPEDICION", re.IGNORECASE),
    )
    ENCABEZADO_TABLA = re.compile(r"CANT\.?\s*DESCRIPCION", re.IGNORECASE)
    CIERRE = re.compile(r"^\s*TOTAL\s*:", re.IGNORECASE)

    def puntaje(self, lineas: Sequence[str]) -> float:
        texto = "\n".join(lineas)
        encontradas = sum(1 for huella in self.HUELLAS if huella.search(texto))
        return encontradas / len(self.HUELLAS)

    def localizar_productos(self, lineas: Sequence[str]) -> BloqueDeProductos | None:
        inicio = fin = None
        for indice, linea in enumerate(lineas):
            if inicio is None and self.ENCABEZADO_TABLA.search(linea):
                inicio = indice + 1
            elif inicio is not None and self.CIERRE.search(linea):
                fin = indice
                break
        if inicio is None:
            return None
        return BloqueDeProductos(inicio, fin if fin is not None else len(lineas))


class PerfilMiyabi(PerfilDeTicket):
    """Plantilla con columna de `$` separada y la linea de IVA suelta.

    No lleva el nombre de un POS porque el ticket no lo declara; lo identifica
    el encabezado de tabla con IMPORTE y la ausencia de las huellas de SOFT.
    """

    ENCABEZADO_TABLA = re.compile(r"CANT\.?\s*DESCRIPCION.*IMPORTE", re.IGNORECASE)
    CIERRE = re.compile(r"^\s*(TOTAL|IVA)\s*:", re.IGNORECASE)

    def puntaje(self, lineas: Sequence[str]) -> float:
        texto = "\n".join(lineas)
        if PerfilSoftRestaurant().puntaje(lineas) > 0.5:
            return 0.0
        marcas = [
            self.ENCABEZADO_TABLA.search(texto) is not None,
            re.search(r"\bRFC\b", texto, re.IGNORECASE) is not None,
            re.search(r"^\s*IVA\s*:", texto, re.IGNORECASE | re.MULTILINE) is not None,
        ]
        return sum(marcas) / len(marcas)

    def localizar_productos(self, lineas: Sequence[str]) -> BloqueDeProductos | None:
        inicio = fin = None
        for indice, linea in enumerate(lineas):
            if inicio is None and self.ENCABEZADO_TABLA.search(linea):
                inicio = indice + 1
            elif inicio is not None and self.CIERRE.search(linea):
                fin = indice
                break
        if inicio is None:
            return None
        return BloqueDeProductos(inicio, fin if fin is not None else len(lineas))


class PerfilGenerico(PerfilDeTicket):
    """Ultimo recurso: sin estructura conocida, decide la heuristica por linea."""

    def puntaje(self, lineas: Sequence[str]) -> float:
        return 0.05

    def localizar_productos(self, lineas: Sequence[str]) -> BloqueDeProductos | None:
        return None


class DetectorDePerfil:
    """Elige el perfil con mayor puntaje; `PerfilGenerico` siempre empata al fondo."""

    def __init__(self, perfiles: Sequence[PerfilDeTicket] | None = None) -> None:
        self.perfiles = list(perfiles) if perfiles else [
            PerfilSoftRestaurant(), PerfilMiyabi(), PerfilGenerico()
        ]

    def detectar(self, lineas: Sequence[str]) -> tuple[PerfilDeTicket, float]:
        puntuados = [(perfil, perfil.puntaje(lineas)) for perfil in self.perfiles]
        return max(puntuados, key=lambda par: par[1])

    def diagnostico(self, lineas: Sequence[str]) -> dict[str, float]:
        return {p.nombre: round(p.puntaje(lineas), 3) for p in self.perfiles}
