"""Genera recortes reales etiquetados a partir de las fotos y sus transcripciones."""
import sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, "tests")

from divieat_ticket.modelo.reales import EtiquetadorDeRecortesReales
from divieat_ticket.modelo.segmentacion import SegmentadorNeuronal
from divieat_ticket.ocr import MotorEasyOCR, SegmentadorPorMotorOCR
from divieat_ticket.preproceso import CadenaDePreproceso
import fixtures_reales as fx

CARPETA_FOTOS = Path("datos/reales")
fotos = []
for caso in fx.TODOS:
    ruta = CARPETA_FOTOS / f"{caso.nombre}.png"
    if ruta.is_file():
        fotos.append((caso.nombre, ruta, caso.lineas))
    else:
        print(f"  (sin foto: {caso.nombre})")

print(f"{len(fotos)} fotos con transcripcion\n", flush=True)
# Las cajas vienen del motor que de verdad lee fotos reales; la U-Net propia
# todavia funde la tabla de productos en una sola mancha sobre papel real.
motor = MotorEasyOCR()
etiquetador = EtiquetadorDeRecortesReales(
    "datos/corpus_reales",
    cadena=CadenaDePreproceso.por_defecto(),
    segmentador=SegmentadorPorMotorOCR(motor),
    motor=motor,
)
print(etiquetador.etiquetar(fotos))
