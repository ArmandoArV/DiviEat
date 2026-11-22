"""Objetos de dominio del ticket.

Todo el dinero vive en **centavos enteros**: los flotantes rompen el cuadre
(0.1 + 0.2 != 0.3) y el cuadre es justamente lo que decide si al comensal le
mostramos la pantalla «Revisar lo detectado» en verde o en ambar.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


class ErrorDeDominio(ValueError):
    """Dato que no puede representarse en el dominio (importe imposible, etc.)."""


@dataclass(frozen=True, order=True)
class Dinero:
    """Importe en pesos mexicanos, guardado como centavos enteros."""

    centavos: int

    _PATRON = re.compile(
        r"""
        (?P<signo>-)?\s*
        \$?\s*
        (?P<entero>\d{1,3}(?:[.,\s]\d{3})+|\d+)
        (?:(?P<sep>[.,])(?P<decimal>\d{2}))?
        \s*(?:MXN|M\.N\.|PESOS)?
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.centavos, int):
            raise ErrorDeDominio(f"los centavos deben ser int, llego {type(self.centavos)!r}")

    # ---------------------------------------------------------------- fabricas
    @classmethod
    def cero(cls) -> "Dinero":
        return cls(0)

    @classmethod
    def desde_pesos(cls, pesos: float | int | str) -> "Dinero":
        """Acepta 240, 240.5, "240.50". Redondea al centavo mas cercano."""
        if isinstance(pesos, str):
            analizado = cls.desde_texto(pesos)
            if analizado is None:
                raise ErrorDeDominio(f"no pude leer un importe en {pesos!r}")
            return analizado
        return cls(int(round(float(pesos) * 100)))

    @classmethod
    def desde_texto(cls, texto: str | None) -> "Dinero | None":
        """Extrae el importe de un fragmento de OCR. Devuelve None si no hay ninguno.

        Resuelve la ambiguedad de separadores: dos digitos tras el ultimo
        separador lo vuelven decimal; en otro caso todos son separadores de miles.
        """
        if not texto:
            return None
        coincidencia = cls._PATRON.search(texto.strip())
        if coincidencia is None:
            return None

        entero = re.sub(r"[.,\s]", "", coincidencia.group("entero"))
        if not entero.isdigit():
            return None
        decimal = coincidencia.group("decimal") or "00"
        centavos = int(entero) * 100 + int(decimal)
        if coincidencia.group("signo"):
            centavos = -centavos
        return cls(centavos)

    # ------------------------------------------------------------- operaciones
    def __add__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.centavos + otro.centavos)

    def __sub__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.centavos - otro.centavos)

    def __mul__(self, factor: int) -> "Dinero":
        if not isinstance(factor, int):
            raise ErrorDeDominio("solo se puede multiplicar un importe por un entero")
        return Dinero(self.centavos * factor)

    __rmul__ = __mul__

    def __abs__(self) -> "Dinero":
        return Dinero(abs(self.centavos))

    def __bool__(self) -> bool:
        return self.centavos != 0

    @property
    def pesos(self) -> float:
        """Solo para presentacion; no uses esto para sumar."""
        return self.centavos / 100

    def __str__(self) -> str:
        signo = "-" if self.centavos < 0 else ""
        entero, decimal = divmod(abs(self.centavos), 100)
        return f"{signo}${entero:,}.{decimal:02d}"

    def __repr__(self) -> str:
        return f"Dinero({self.centavos})  # {self}"

    @classmethod
    def suma(cls, importes: Iterable["Dinero"]) -> "Dinero":
        return cls(sum(i.centavos for i in importes))


@dataclass
class Producto:
    """Una linea de consumo del ticket."""

    descripcion: str
    cantidad: int
    importe: Dinero
    precio_unitario: Dinero | None = None
    confianza: float = 1.0
    linea: int | None = None

    def __post_init__(self) -> None:
        self.descripcion = " ".join(self.descripcion.split())
        if self.cantidad < 1:
            raise ErrorDeDominio(f"cantidad invalida ({self.cantidad}) en {self.descripcion!r}")
        if self.precio_unitario is None and self.importe.centavos % self.cantidad == 0:
            self.precio_unitario = Dinero(self.importe.centavos // self.cantidad)

    @property
    def unitario_cuadra(self) -> bool:
        """cantidad x unitario == importe. Si no, el OCR leyo mal algun numero."""
        if self.precio_unitario is None:
            return True
        return self.precio_unitario * self.cantidad == self.importe

    def es_dudoso(self, umbral: float = 0.80) -> bool:
        return self.confianza < umbral or not self.unitario_cuadra

    def a_dict(self) -> dict[str, Any]:
        return {
            "descripcion": self.descripcion,
            "cantidad": self.cantidad,
            "precio_unitario_centavos": (
                self.precio_unitario.centavos if self.precio_unitario else None
            ),
            "importe_centavos": self.importe.centavos,
            "confianza": round(self.confianza, 4),
            "linea": self.linea,
        }

    def __str__(self) -> str:
        marca = " !" if self.es_dudoso() else ""
        return f"{self.cantidad:>2} x {self.descripcion:<28} {str(self.importe):>12}{marca}"


@dataclass
class TicketExtraido:
    """Resultado de leer un ticket: alimenta la pantalla «Revisar lo detectado»."""

    productos: list[Producto] = field(default_factory=list)
    restaurante: str | None = None
    fecha: datetime | None = None
    folio: str | None = None
    subtotal: Dinero | None = None
    propina: Dinero | None = None
    total_impreso: Dinero | None = None
    iva: Dinero | None = None
    mesa: str | None = None
    comensales: int | None = None
    perfil_pos: str | None = None
    motor_ocr: str | None = None

    TOLERANCIA_POR_DEFECTO = Dinero(100)

    @property
    def suma_productos(self) -> Dinero:
        return Dinero.suma(p.importe for p in self.productos)

    @property
    def total_de_referencia(self) -> Dinero | None:
        """Contra que cuadramos la suma de los productos.

        En Mexico el precio de carta ya trae el IVA incluido: en los tickets
        reales (SOFT RESTAURANT, Miyabi) la suma de los renglones da el TOTAL,
        mientras que el SUBTOTAL es la base gravable *antes* del impuesto
        (subtotal + IVA = total). Por eso manda el TOTAL y no el subtotal.
        Si la propina viene sumada dentro del total, se descuenta.
        """
        if self.total_impreso is not None:
            referencia = self.total_impreso
            if self.propina is not None and self.propina.centavos > 0:
                referencia = referencia - self.propina
            return referencia
        return self.subtotal

    def diferencia(self) -> Dinero | None:
        referencia = self.total_de_referencia
        if referencia is None:
            return None
        return self.suma_productos - referencia

    def cuadra(self, tolerancia: Dinero | None = None) -> bool:
        """True si la suma de los productos coincide con el total impreso.

        Sin total legible devolvemos False: no podemos afirmar que cuadra, y
        prometerlo en la UI seria mentir.
        """
        diferencia = self.diferencia()
        if diferencia is None:
            return False
        limite = tolerancia or self.TOLERANCIA_POR_DEFECTO
        return abs(diferencia).centavos <= limite.centavos

    def productos_dudosos(self, umbral: float = 0.80) -> list[Producto]:
        return [p for p in self.productos if p.es_dudoso(umbral)]

    def a_dict(self) -> dict[str, Any]:
        diferencia = self.diferencia()
        return {
            "restaurante": self.restaurante,
            "fecha": self.fecha.isoformat(timespec="seconds") if self.fecha else None,
            "folio": self.folio,
            "mesa": self.mesa,
            "comensales": self.comensales,
            "perfil_pos": self.perfil_pos,
            "motor_ocr": self.motor_ocr,
            "productos": [p.a_dict() for p in self.productos],
            "subtotal_centavos": self.subtotal.centavos if self.subtotal else None,
            "propina_centavos": self.propina.centavos if self.propina else None,
            "total_impreso_centavos": self.total_impreso.centavos if self.total_impreso else None,
            "iva_centavos": self.iva.centavos if self.iva else None,
            "cuadre": {
                "suma_productos_centavos": self.suma_productos.centavos,
                "diferencia_centavos": diferencia.centavos if diferencia else None,
                "cuadra": self.cuadra(),
            },
        }

    def a_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.a_dict(), ensure_ascii=False, indent=indent)

    def __str__(self) -> str:
        cabecera = self.restaurante or "(restaurante no identificado)"
        if self.fecha:
            cabecera += f"  ·  {self.fecha:%d/%m/%Y %H:%M}"
        filas = "\n".join(str(p) for p in self.productos) or "  (sin productos)"
        diferencia = self.diferencia()
        if diferencia is None:
            cuadre = "sin total impreso legible: no se puede cuadrar"
        elif self.cuadra():
            cuadre = f"cuadra con el ticket ({self.total_de_referencia})"
        else:
            cuadre = f"NO cuadra: diferencia de {diferencia} contra {self.total_de_referencia}"
        return (
            f"{cabecera}\n{'-' * 52}\n{filas}\n{'-' * 52}\n"
            f"{len(self.productos)} productos · suma {self.suma_productos}\n{cuadre}"
        )
