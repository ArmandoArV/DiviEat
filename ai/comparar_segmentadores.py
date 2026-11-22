"""Morfologia vs U-Net: cuantos tickets quedan con el numero exacto de renglones."""
import sys, time
from collections import Counter
sys.path.insert(0, "src")

from divieat_ticket.ocr import SegmentadorMorfologico, SegmentadorPorProyeccion
from divieat_ticket.modelo.segmentacion import SegmentadorNeuronal
from divieat_ticket.preproceso import CadenaDePreproceso
from divieat_ticket.sintetico import ConfiguracionSintetico, GeneradorTicketsSinteticos

TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 40
cadena = CadenaDePreproceso.por_defecto()

candidatos = [
    ("proyeccion", SegmentadorPorProyeccion(), True),
    ("morfologico", SegmentadorMorfologico(), True),
    ("U-Net", SegmentadorNeuronal(), False),   # la red ve la imagen sin binarizar
]
for etiqueta, segmentador, usa_cadena in candidatos:
    if hasattr(segmentador, "disponible") and not segmentador.disponible():
        print(f"{etiqueta:<12} no disponible (falta modelos/unet.pt)")
        continue
    generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=101))
    dif = Counter()
    inicio = time.perf_counter()
    for _ in range(TOTAL):
        muestra = generador.generar()
        entrada = cadena.aplicar(muestra.imagen) if usa_cadena else muestra.imagen
        cajas = segmentador.segmentar(entrada)
        dif[len(cajas) - len(muestra.renglones)] += 1
    exacto = dif[0]
    cerca = sum(v for k, v in dif.items() if abs(k) <= 1)
    print(f"{etiqueta:<12} exacto {exacto:>2}/{TOTAL} ({exacto/TOTAL:.0%}) · "
          f"+-1 renglon {cerca/TOTAL:.0%} · {(time.perf_counter()-inicio)/TOTAL:.2f}s/ticket")
    print(f"             distribucion {dict(sorted(dif.items()))}")
