"""Linea de comandos del extractor de tickets.

    python -m divieat_ticket.cli motores
    python -m divieat_ticket.cli generar --cantidad 20 --salida datos/sinteticos
    python -m divieat_ticket.cli extraer foto.jpg --trazas salida/
    python -m divieat_ticket.cli fixtures
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from divieat_ticket.imagen import Imagen
from divieat_ticket.ocr import MotorEasyOCR, MotorTesseract, SelectorDeMotor
from divieat_ticket.parser import AnalizadorDeTicket
from divieat_ticket.pipeline import PipelineExtraccionTicket
from divieat_ticket.sintetico import ConfiguracionSintetico, GeneradorTicketsSinteticos


class Comando:
    """Un subcomando del CLI."""

    nombre = ""
    ayuda = ""

    def configurar(self, analizador: argparse.ArgumentParser) -> None:
        ...

    def ejecutar(self, args: argparse.Namespace) -> int:
        raise NotImplementedError


class ComandoMotores(Comando):
    nombre = "motores"
    ayuda = "lista los motores OCR disponibles en este equipo"

    def ejecutar(self, args: argparse.Namespace) -> int:
        selector = SelectorDeMotor([MotorTesseract(), MotorEasyOCR()])
        for motor in selector.motores:
            estado = "disponible" if motor.disponible() else "no instalado"
            print(f"  {motor.nombre:<16} {estado}")
        disponibles = selector.disponibles()
        if not disponibles:
            print("\nNinguno instalado. Opciones:")
            print("  uv pip install --python .venv/bin/python easyocr   (CRNN preentrenada)")
            print("  brew install tesseract tesseract-lang              (motor clasico)")
        return 0


class ComandoGenerar(Comando):
    nombre = "generar"
    ayuda = "fabrica tickets sinteticos con verdad de referencia"

    def configurar(self, analizador: argparse.ArgumentParser) -> None:
        analizador.add_argument("--cantidad", type=int, default=10)
        analizador.add_argument("--salida", type=Path, default=Path("datos/sinteticos"))
        analizador.add_argument("--semilla", type=int, default=7)
        analizador.add_argument("--limpios", action="store_true", help="sin degradacion")

    def ejecutar(self, args: argparse.Namespace) -> int:
        generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=args.semilla))
        for indice in range(args.cantidad):
            muestra = generador.generar(degradar=not args.limpios)
            muestra.guardar(args.salida, f"ticket_{indice:04d}")
        print(f"{args.cantidad} tickets en {args.salida}")
        return 0


class ComandoExtraer(Comando):
    nombre = "extraer"
    ayuda = "lee una foto de ticket y escribe el JSON estructurado"

    def configurar(self, analizador: argparse.ArgumentParser) -> None:
        analizador.add_argument("imagen", type=Path)
        analizador.add_argument("--trazas", type=Path, help="carpeta para los pasos intermedios")
        analizador.add_argument("--json", type=Path, help="archivo de salida")

    def ejecutar(self, args: argparse.Namespace) -> int:
        try:
            pipeline = PipelineExtraccionTicket.automatico()
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

        resultado = pipeline.procesar_con_trazas(args.imagen)
        print(f"motor: {resultado.ocr.motor} · perfil: {resultado.perfil}")
        print(resultado.ticket)
        if args.trazas:
            resultado.guardar_trazas(args.trazas)
            print(f"\ntrazas en {args.trazas}")
        if args.json:
            args.json.write_text(resultado.ticket.a_json(), encoding="utf-8")
            print(f"json en {args.json}")
        return 0 if resultado.ticket.cuadra() else 1


class ComandoFixtures(Comando):
    nombre = "fixtures"
    ayuda = "analiza los tickets reales transcritos (sin OCR)"

    def ejecutar(self, args: argparse.Namespace) -> int:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
        from fixtures_reales import TODOS  # noqa: PLC0415
        from divieat_ticket.ocr import MotorDeReferencia  # noqa: PLC0415

        lienzo = Imagen(np.zeros((10, 10), np.uint8))
        fallos = 0
        for caso in TODOS:
            analizador = AnalizadorDeTicket()
            ticket = analizador.analizar(MotorDeReferencia(caso.lineas).reconocer(lienzo))
            cuadra = ticket.cuadra() and len(ticket.productos) == caso.productos_esperados
            fallos += 0 if cuadra else 1
            print(f"[{'ok ' if cuadra else 'FAIL'}] {caso.nombre:<10} {analizador.ultimo_perfil.nombre:<22} "
                  f"{len(ticket.productos)} productos · {ticket.suma_productos} / {ticket.total_impreso}")
        return 1 if fallos else 0


class ComandoEvaluar(Comando):
    nombre = "evaluar"
    ayuda = "mide los motores disponibles sobre tickets sinteticos"

    def configurar(self, analizador: argparse.ArgumentParser) -> None:
        analizador.add_argument("--cantidad", type=int, default=12)
        analizador.add_argument("--modelo", type=Path, default=Path("modelos/crnn.pt"))

    def ejecutar(self, args: argparse.Namespace) -> int:
        from divieat_ticket.evaluacion import EvaluadorDeExtraccion  # noqa: PLC0415
        from divieat_ticket.ocr import MotorCRNN  # noqa: PLC0415
        from divieat_ticket.preproceso import CadenaDePreproceso  # noqa: PLC0415

        evaluador = EvaluadorDeExtraccion()
        muestras = evaluador.muestras(args.cantidad)
        motores = [MotorCRNN(str(args.modelo)), MotorEasyOCR(), MotorTesseract()]
        for motor in motores:
            if not motor.disponible():
                print(f"{motor.nombre:<16} no disponible")
                continue
            pipeline = PipelineExtraccionTicket(motor, CadenaDePreproceso.por_defecto())
            print(evaluador.evaluar(pipeline, muestras))
        return 0


class AplicacionCLI:
    """Registro de comandos y despacho."""

    def __init__(self, comandos: list[Comando] | None = None) -> None:
        self.comandos = comandos or [
            ComandoMotores(), ComandoGenerar(), ComandoExtraer(),
            ComandoFixtures(), ComandoEvaluar(),
        ]

    def construir(self) -> argparse.ArgumentParser:
        raiz = argparse.ArgumentParser(
            prog="divieat-ticket", description="Extraccion de informacion de tickets (DiviEat)"
        )
        subcomandos = raiz.add_subparsers(dest="comando", required=True)
        for comando in self.comandos:
            sub = subcomandos.add_parser(comando.nombre, help=comando.ayuda)
            comando.configurar(sub)
            sub.set_defaults(_ejecutor=comando)
        return raiz

    def correr(self, argv: list[str] | None = None) -> int:
        args = self.construir().parse_args(argv)
        return args._ejecutor.ejecutar(args)


def main() -> int:
    return AplicacionCLI().correr()


if __name__ == "__main__":
    raise SystemExit(main())
