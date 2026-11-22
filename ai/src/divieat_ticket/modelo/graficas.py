"""Curvas de aprendizaje y diagnostico de sobreajuste.

La perdida de entrenamiento sola no dice nada sobre generalizacion: siempre
puede bajar memorizando. El diagnostico del curso compara las dos curvas:

* ambas altas y aun bajando .......... subajuste (falta capacidad o epocas)
* ambas bajas y pegadas ............. buen ajuste
* entrenamiento baja, validacion sube  sobreajuste (memoriza el conjunto)

La epoca util es donde la validacion toca su minimo; lo que viene despues es
memorizacion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from divieat_ticket.modelo.entrenamiento import RegistroEpoca  # noqa: E402

NARANJA = "#FF7A1A"
CAFE = "#3A2E26"
VERDE = "#12A150"
TEAL = "#0FA3A3"
ROJO = "#F2484B"


@dataclass(frozen=True)
class VeredictoSobreajuste:
    etiqueta: str
    epoca_optima: int
    perdida_minima_validacion: float
    repunte: float
    brecha_final: float
    explicacion: str

    def __str__(self) -> str:
        return (f"{self.etiqueta.upper()} · epoca optima {self.epoca_optima} · "
                f"repunte {self.repunte:+.3f} · brecha final {self.brecha_final:+.3f}\n"
                f"  {self.explicacion}")


class DiagnosticoDeSobreajuste:
    """Aplica las reglas de lectura de curvas sobre un historial."""

    def __init__(
        self,
        historial: Sequence[RegistroEpoca],
        tolerancia_repunte: float = 0.02,
        tolerancia_brecha: float = 0.25,
    ) -> None:
        if not historial:
            raise ValueError("historial vacio")
        self.historial = list(historial)
        self.tolerancia_repunte = tolerancia_repunte
        self.tolerancia_brecha = tolerancia_brecha

    @property
    def epoca_optima(self) -> int:
        mejor = min(self.historial, key=lambda r: r.perdida_validacion)
        return mejor.epoca

    @property
    def repunte(self) -> float:
        """Cuanto subio la perdida de validacion desde su minimo hasta el final."""
        minima = min(r.perdida_validacion for r in self.historial)
        return self.historial[-1].perdida_validacion - minima

    def veredicto(self) -> VeredictoSobreajuste:
        ultimo = self.historial[-1]
        minima = min(r.perdida_validacion for r in self.historial)
        repunte = self.repunte
        brecha = ultimo.brecha

        if repunte > self.tolerancia_repunte:
            etiqueta = "sobreajuste"
            explicacion = (
                f"la validacion toco su minimo en la epoca {self.epoca_optima} y desde ahi "
                f"subio {repunte:.3f} mientras el entrenamiento siguio bajando: la red "
                f"empezo a memorizar. Entrena hasta la epoca {self.epoca_optima}."
            )
        elif brecha > self.tolerancia_brecha:
            etiqueta = "sobreajuste leve"
            explicacion = (
                f"la validacion no repunta, pero queda {brecha:.3f} por encima del "
                "entrenamiento: hay margen para mas datos o mas aumentacion."
            )
        elif ultimo.perdida_validacion > 1.0 and len(self.historial) >= 3:
            etiqueta = "subajuste"
            explicacion = (
                "las dos perdidas siguen altas: falta capacidad, tasa de aprendizaje "
                "o mas epocas."
            )
        else:
            etiqueta = "buen ajuste"
            explicacion = (
                f"las curvas bajan juntas y terminan pegadas (brecha {brecha:+.3f}); "
                "la aumentacion esta cubriendo la variabilidad del dominio."
            )
        return VeredictoSobreajuste(
            etiqueta=etiqueta,
            epoca_optima=self.epoca_optima,
            perdida_minima_validacion=minima,
            repunte=repunte,
            brecha_final=brecha,
            explicacion=explicacion,
        )


class GraficadorDeAprendizaje:
    """Dibuja las curvas de un entrenamiento."""

    def __init__(
        self, historial: Sequence[RegistroEpoca], titulo: str = "",
        nombre_metrica: str = "CER",
        nombre_perdida: str = "Perdida CTC",
    ) -> None:
        self.historial = list(historial)
        self.titulo = titulo
        self.nombre_metrica = nombre_metrica
        self.nombre_perdida = nombre_perdida

    def figura(self, ruta: str | Path) -> Path:
        epocas = [r.epoca for r in self.historial]
        diagnostico = DiagnosticoDeSobreajuste(self.historial).veredicto()

        figura, ejes = plt.subplots(1, 3, figsize=(15, 4.4))
        self._panel_perdida(ejes[0], epocas, diagnostico)
        self._panel_cer(ejes[1], epocas, diagnostico)
        self._panel_brecha(ejes[2], epocas)

        figura.suptitle(
            f"{self.titulo}  —  {diagnostico.etiqueta}", fontsize=13, color=CAFE, y=1.02
        )
        figura.tight_layout()
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        figura.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(figura)
        return ruta

    def _panel_perdida(self, eje, epocas, diagnostico) -> None:
        eje.plot(epocas, [r.perdida_entrenamiento for r in self.historial],
                 "-o", color=NARANJA, label="entrenamiento", markersize=4)
        eje.plot(epocas, [r.perdida_validacion for r in self.historial],
                 "-s", color=TEAL, label="validacion", markersize=4)
        eje.axvline(diagnostico.epoca_optima, color=ROJO, linestyle="--", linewidth=1.2,
                    label=f"minimo val (epoca {diagnostico.epoca_optima})")
        eje.set_title(self.nombre_perdida)
        eje.set_xlabel("epoca"); eje.set_ylabel("perdida")
        eje.legend(fontsize=8); eje.grid(alpha=0.3)

    def _panel_cer(self, eje, epocas, diagnostico) -> None:
        eje.plot(epocas, [r.cer_entrenamiento for r in self.historial],
                 "-o", color=NARANJA, label="entrenamiento", markersize=4)
        eje.plot(epocas, [r.cer_validacion for r in self.historial],
                 "-s", color=TEAL, label="validacion", markersize=4)
        eje.set_title(self.nombre_metrica)
        eje.set_xlabel("epoca"); eje.set_ylabel("error")
        eje.legend(fontsize=8); eje.grid(alpha=0.3)

    def _panel_brecha(self, eje, epocas) -> None:
        brechas = [r.brecha for r in self.historial]
        colores = [ROJO if b > 0 else VERDE for b in brechas]
        eje.bar(epocas, brechas, color=colores, alpha=0.75)
        eje.axhline(0, color=CAFE, linewidth=1)
        eje.set_title("Brecha de generalizacion (val - entren.)")
        eje.set_xlabel("epoca"); eje.set_ylabel("diferencia de perdida")
        eje.grid(alpha=0.3, axis="y")


class ComparadorDeCurvas:
    """Superpone varios experimentos para ver el efecto de una decision."""

    PALETA = (NARANJA, TEAL, VERDE, ROJO)

    def __init__(self, experimentos: Mapping[str, Sequence[RegistroEpoca]]) -> None:
        self.experimentos = dict(experimentos)

    def figura(self, ruta: str | Path, titulo: str = "") -> Path:
        figura, ejes = plt.subplots(1, 2, figsize=(12, 4.4))
        for indice, (nombre, historial) in enumerate(self.experimentos.items()):
            color = self.PALETA[indice % len(self.PALETA)]
            epocas = [r.epoca for r in historial]
            ejes[0].plot(epocas, [r.perdida_entrenamiento for r in historial],
                         "--", color=color, alpha=0.65, label=f"{nombre} · entren.")
            ejes[0].plot(epocas, [r.perdida_validacion for r in historial],
                         "-o", color=color, markersize=4, label=f"{nombre} · valid.")
            ejes[1].plot(epocas, [r.cer_validacion for r in historial],
                         "-o", color=color, markersize=4, label=nombre)
        ejes[0].set_title("Perdida CTC"); ejes[0].set_xlabel("epoca")
        ejes[0].legend(fontsize=8); ejes[0].grid(alpha=0.3)
        ejes[1].set_title("CER de validacion"); ejes[1].set_xlabel("epoca")
        ejes[1].legend(fontsize=8); ejes[1].grid(alpha=0.3)
        if titulo:
            figura.suptitle(titulo, fontsize=13, color=CAFE, y=1.02)
        figura.tight_layout()
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        figura.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(figura)
        return ruta

    def tabla(self) -> str:
        filas = ["experimento        epocas  val min  CER val  brecha  veredicto"]
        for nombre, historial in self.experimentos.items():
            d = DiagnosticoDeSobreajuste(historial).veredicto()
            cer = min(r.cer_validacion for r in historial)
            filas.append(
                f"{nombre:<18} {len(historial):>6}  {d.perdida_minima_validacion:7.3f}  "
                f"{cer:7.4f}  {d.brecha_final:+6.3f}  {d.etiqueta}"
            )
        return "\n".join(filas)
