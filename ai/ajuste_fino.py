"""Ajuste fino de la CRNN sobre los recortes del pipeline real.

Transferencia de conocimiento (Clase 2 de Deep Learning Avanzado): se parte de
los pesos entrenados con renglones limpios y se adapta al dominio de llegada
con una tasa de aprendizaje baja, en vez de entrenar de cero.
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

import torch

from divieat_ticket.modelo.entrenamiento import (
    ConfiguracionEntrenamiento, EntrenadorCRNN, FuenteCorpus,
)
from divieat_ticket.modelo.graficas import DiagnosticoDeSobreajuste, GraficadorDeAprendizaje

BASE = Path("modelos/crnn.pt")
modelo, alfabeto, cer_previo = EntrenadorCRNN.cargar_modelo(BASE)
print(f"punto de partida: {BASE} · CER en renglones limpios {cer_previo:.4f}", flush=True)

config = ConfiguracionEntrenamiento(
    epocas=18,
    tamano_lote=32,
    tasa_aprendizaje=2e-4,          # baja: es adaptacion, no aprendizaje de cero
    paciencia=4,
    ruta_checkpoint=Path("modelos/crnn_unet.pt"),
)
entrenador = EntrenadorCRNN(
    modelo=modelo, alfabeto=alfabeto, config=config,
    fuente=FuenteCorpus("datos/corpus_unet2"),
)
entrenamiento, validacion, _ = entrenador.cargadores()
print(f"corpus: {len(entrenamiento.dataset)} entrenamiento · {len(validacion.dataset)} validacion")
print(f"CER del modelo base sobre recortes del pipeline: "
      f"{entrenador.evaluar(validacion).tasa:.4f}  <- el salto de dominio", flush=True)

entrenador.entrenar()
ruta = GraficadorDeAprendizaje(entrenador.historial, "CRNN · ajuste fino sobre recortes de la U-Net").figura(
    "figuras/curvas_ajuste_unet.png"
)
print(f"\nfigura: {ruta}")
print(DiagnosticoDeSobreajuste(entrenador.historial).veredicto())
