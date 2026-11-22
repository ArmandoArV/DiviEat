"""Reconstruye la tuberia entera sobre el dominio correcto.

La leccion de los dos saltos de dominio anteriores: la red tiene que entrenarse
con **exactamente** lo que vera en inferencia. Aqui se encadena todo en ese
orden: mascaras sobre imagen corregida -> U-Net -> recortes de esa U-Net ->
CRNN sobre esos recortes.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, "src")

from divieat_ticket.modelo.corpus import ConstructorDeCorpus
from divieat_ticket.modelo.entrenamiento import (
    ConfiguracionEntrenamiento, EntrenadorCRNN, FuenteCorpus,
)
from divieat_ticket.modelo.graficas import DiagnosticoDeSobreajuste, GraficadorDeAprendizaje
from divieat_ticket.modelo.segmentacion import (
    ConfiguracionUNet, ConstructorDeMascaras, EntrenadorUNet, SegmentadorNeuronal,
)
from divieat_ticket.preproceso import CadenaDePreproceso

reloj = time.perf_counter()
cadena = CadenaDePreproceso.por_defecto()

print("=" * 60, "\n1/4 · mascaras sobre imagen corregida", flush=True)
print(ConstructorDeMascaras("datos/mascaras_final", semilla=31, cadena=cadena).construir(800))

print("=" * 60, "\n2/4 · U-Net", flush=True)
entrenador_unet = EntrenadorUNet(ConfiguracionUNet(
    epocas=26, carpeta_corpus="datos/mascaras_final", ruta_checkpoint=Path("modelos/unet_final.pt")
))
entrenador_unet.entrenar()
GraficadorDeAprendizaje(
    entrenador_unet.historial, "U-Net · renglones sobre imagen corregida",
    nombre_metrica="Error de segmentacion (1 - IoU)", nombre_perdida="Perdida BCE + Dice",
).figura("figuras/curvas_unet_final.png")

print("=" * 60, "\n3/4 · recortes con la U-Net", flush=True)
constructor = ConstructorDeCorpus(
    "datos/corpus_final", cadena=cadena,
    segmentador=SegmentadorNeuronal("modelos/unet_final.pt"), semilla=41,
)
print(constructor.construir(7000))

print("=" * 60, "\n4/4 · ajuste fino de la CRNN", flush=True)
modelo, alfabeto, _ = EntrenadorCRNN.cargar_modelo("modelos/crnn.pt")
entrenador = EntrenadorCRNN(
    modelo=modelo, alfabeto=alfabeto,
    config=ConfiguracionEntrenamiento(
        epocas=20, tasa_aprendizaje=2e-4, paciencia=5,
        ruta_checkpoint=Path("modelos/crnn_final.pt"),
    ),
    fuente=FuenteCorpus("datos/corpus_final"),
)
_, validacion, _ = entrenador.cargadores()
print(f"CER del modelo base sobre estos recortes: {entrenador.evaluar(validacion).tasa:.4f}", flush=True)
entrenador.entrenar()
GraficadorDeAprendizaje(entrenador.historial, "CRNN · recortes de la U-Net").figura(
    "figuras/curvas_crnn_final.png"
)
print(DiagnosticoDeSobreajuste(entrenador.historial).veredicto())
print(f"\ntiempo total: {(time.perf_counter()-reloj)/60:.1f} min")
