"""Corpus de renglones usando el segmentador que de verdad se usara."""
import sys
sys.path.insert(0, "src")

from divieat_ticket.modelo.corpus import ConstructorDeCorpus
from divieat_ticket.modelo.segmentacion import SegmentadorNeuronal
from divieat_ticket.preproceso import CadenaDePreproceso, EscalaDeGrises, EscaladoAAlto

objetivo = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
# La U-Net trabaja sobre la imagen cruda: solo se normaliza tamano y color.
cadena = CadenaDePreproceso([EscaladoAAlto(1600), EscalaDeGrises()])
constructor = ConstructorDeCorpus(
    "datos/corpus_unet2", cadena=cadena, segmentador=SegmentadorNeuronal(), semilla=41
)
print(f"objetivo: {objetivo} recortes · segmentador U-Net", flush=True)
print(constructor.construir(objetivo))
