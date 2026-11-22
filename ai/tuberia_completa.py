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

print("=" * 60, "\n0/5 · CRNN sobre renglones de plantilla real", flush=True)
base = EntrenadorCRNN(config=ConfiguracionEntrenamiento(
    epocas=14, muestras_entrenamiento=12_000, muestras_validacion=800,
    tasa_aprendizaje=3e-4, ruta_checkpoint=Path("modelos/crnn_v2.pt"),
))
print(f"dispositivo: {base.dispositivo}", flush=True)
base.entrenar()
GraficadorDeAprendizaje(base.historial, "CRNN · renglones de plantilla real").figura(
    "figuras/curvas_crnn_base_v2.png"
)

print("=" * 60, "\n1/5 · mascaras sobre imagen corregida", flush=True)
print(ConstructorDeMascaras("datos/v2_mascaras", semilla=31, cadena=cadena).construir(800))

print("=" * 60, "\n2/5 · U-Net", flush=True)
entrenador_unet = EntrenadorUNet(ConfiguracionUNet(
    epocas=26, carpeta_corpus="datos/v2_mascaras", ruta_checkpoint=Path("modelos/unet_v2.pt")
))
entrenador_unet.entrenar()
GraficadorDeAprendizaje(
    entrenador_unet.historial, "U-Net · renglones sobre imagen corregida",
    nombre_metrica="Error de segmentacion (1 - IoU)", nombre_perdida="Perdida BCE + Dice",
).figura("figuras/curvas_unet_v2.png")

print("=" * 60, "\n3/5 · recortes con la U-Net", flush=True)
constructor = ConstructorDeCorpus(
    "datos/v2_corpus", cadena=cadena,
    segmentador=SegmentadorNeuronal("modelos/unet_v2.pt"), semilla=41,
)
print(constructor.construir(7000))

print("=" * 60, "\n4/5 · ajuste fino de la CRNN", flush=True)
modelo, alfabeto, _ = EntrenadorCRNN.cargar_modelo("modelos/crnn_v2.pt")
entrenador = EntrenadorCRNN(
    modelo=modelo, alfabeto=alfabeto,
    config=ConfiguracionEntrenamiento(
        epocas=20, tasa_aprendizaje=2e-4, paciencia=5,
        ruta_checkpoint=Path("modelos/crnn_v2_final.pt"),
    ),
    fuente=FuenteCorpus("datos/v2_corpus"),
)
_, validacion, _ = entrenador.cargadores()
print(f"CER del modelo base sobre estos recortes: {entrenador.evaluar(validacion).tasa:.4f}", flush=True)
entrenador.entrenar()
GraficadorDeAprendizaje(entrenador.historial, "CRNN · recortes de la U-Net").figura(
    "figuras/curvas_crnn_v2_final.png"
)
print(DiagnosticoDeSobreajuste(entrenador.historial).veredicto())
print(f"\ntiempo total: {(time.perf_counter()-reloj)/60:.1f} min")
