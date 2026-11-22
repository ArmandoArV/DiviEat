"""Pipeline de punta a punta: foto -> ticket estructurado."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from divieat_ticket.dominio import TicketExtraido
from divieat_ticket.imagen import Imagen
from divieat_ticket.ocr import MotorEasyOCR, MotorOCR, MotorTesseract, ResultadoOCR, SelectorDeMotor
from divieat_ticket.parser import AnalizadorDeTicket, LineaClasificada
from divieat_ticket.preproceso import CadenaDePreproceso, ConfiguracionPreproceso


@dataclass
class ResultadoPipeline:
    """Salida auditable: el ticket y todo lo que se uso para obtenerlo."""

    ticket: TicketExtraido
    ocr: ResultadoOCR
    clasificadas: list[LineaClasificada] = field(default_factory=list)
    trazas: list[tuple[str, Imagen]] = field(default_factory=list)
    perfil: str | None = None

    def guardar_trazas(self, carpeta: str | Path) -> list[Path]:
        carpeta = Path(carpeta)
        rutas = []
        for indice, (nombre, imagen) in enumerate(self.trazas):
            rutas.append(imagen.guardar(carpeta / f"{indice:02d}_{nombre}.png"))
        return rutas


class PipelineExtraccionTicket:
    """Compone preprocesamiento, OCR y analisis.

    Cada pieza se inyecta, asi que se puede medir el mismo analizador con
    distintos motores (Tesseract, EasyOCR, la CRNN propia) sin tocar nada mas.
    """

    def __init__(
        self,
        motor: MotorOCR,
        cadena: CadenaDePreproceso | None = None,
        analizador: AnalizadorDeTicket | None = None,
    ) -> None:
        self.motor = motor
        self.cadena = cadena or CadenaDePreproceso.por_defecto()
        self.analizador = analizador or AnalizadorDeTicket()

    @classmethod
    def automatico(
        cls, config: ConfiguracionPreproceso | None = None
    ) -> "PipelineExtraccionTicket":
        """Elige el primer motor OCR disponible en el sistema."""
        motor = SelectorDeMotor([MotorTesseract(), MotorEasyOCR()]).elegir()
        return cls(motor, CadenaDePreproceso.por_defecto(config))

    def procesar(self, origen: str | Path | Imagen) -> TicketExtraido:
        return self.procesar_con_trazas(origen).ticket

    def procesar_con_trazas(self, origen: str | Path | Imagen) -> ResultadoPipeline:
        imagen = origen if isinstance(origen, Imagen) else Imagen.desde_archivo(origen)
        trazas = self.cadena.aplicar_con_trazas(imagen)
        preprocesada = trazas[-1][1]

        resultado_ocr = self.motor.reconocer(preprocesada)
        ticket = self.analizador.analizar(resultado_ocr)
        return ResultadoPipeline(
            ticket=ticket,
            ocr=resultado_ocr,
            clasificadas=self.analizador.clasificar(resultado_ocr),
            trazas=trazas,
            perfil=self.analizador.ultimo_perfil.nombre if self.analizador.ultimo_perfil else None,
        )
