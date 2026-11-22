"""Compara motores OCR sobre los mismos tickets sinteticos."""
import sys, time
sys.path.insert(0, "src")

from pathlib import Path

from divieat_ticket.evaluacion import EvaluadorDeExtraccion
from divieat_ticket.ocr import MotorCRNN, MotorEasyOCR, MotorTesseract
from divieat_ticket.modelo.segmentacion import SegmentadorNeuronal
from divieat_ticket.pipeline import PipelineExtraccionTicket
from divieat_ticket.preproceso import CadenaDePreproceso, EscalaDeGrises, EscaladoAAlto

CANTIDAD = int(sys.argv[1]) if len(sys.argv) > 1 else 12

evaluador = EvaluadorDeExtraccion()
muestras = evaluador.muestras(CANTIDAD)
print(f"{CANTIDAD} tickets sinteticos · "
      f"{sum(len(m.verdad.productos) for m in muestras)} productos en total\n")

# La U-Net final trabaja sobre la imagen ya corregida: misma cadena para todos.
clasica = CadenaDePreproceso.por_defecto()

motores = []
if Path("modelos/crnn_pipeline.pt").is_file():
    motores.append(("CRNN+morfologia", MotorCRNN("modelos/crnn_pipeline.pt"), clasica))
if Path("modelos/crnn_v2_final.pt").is_file() and Path("modelos/unet_v2.pt").is_file():
    motores.append((
        "CRNN+U-Net",
        MotorCRNN("modelos/crnn_v2_final.pt",
                  segmentador=SegmentadorNeuronal("modelos/unet_v2.pt")),
        clasica,
    ))
motores += [("EasyOCR", MotorEasyOCR(), clasica), ("Tesseract", MotorTesseract(), clasica)]

for etiqueta, motor, cadena in motores:
    if not motor.disponible():
        print(f"{etiqueta:<16} no disponible")
        continue
    pipeline = PipelineExtraccionTicket(motor, cadena)
    inicio = time.perf_counter()
    resumen = evaluador.evaluar(pipeline, muestras)
    resumen.motor = etiqueta
    print(f"{resumen}  · {(time.perf_counter()-inicio)/CANTIDAD:.2f}s/ticket")
