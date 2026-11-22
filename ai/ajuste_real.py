"""Ajuste fino con recortes reales etiquetados."""
import sys
from pathlib import Path
sys.path.insert(0, "src")

from divieat_ticket.modelo.entrenamiento import (
    ConfiguracionEntrenamiento, EntrenadorCRNN, FuenteMixta,
)
from divieat_ticket.modelo.graficas import DiagnosticoDeSobreajuste, GraficadorDeAprendizaje

modelo, alfabeto, _ = EntrenadorCRNN.cargar_modelo("modelos/crnn_v2_final.pt")
config = ConfiguracionEntrenamiento(
    epocas=16, tamano_lote=16, tasa_aprendizaje=1e-4, paciencia=6,
    ruta_checkpoint=Path("modelos/crnn_real.pt"),
)
entrenador = EntrenadorCRNN(
    modelo=modelo, alfabeto=alfabeto, config=config,
    fuente=FuenteMixta("datos/corpus_reales", "datos/v2_corpus"),
)
entrenamiento, validacion, _ = entrenador.cargadores()
print(f"entrenamiento {len(entrenamiento.dataset)} muestras · "
      f"validacion {len(validacion.dataset)} recortes reales", flush=True)
print(f"CER de partida sobre recortes reales: {entrenador.evaluar(validacion).tasa:.4f}", flush=True)
entrenador.entrenar()
GraficadorDeAprendizaje(entrenador.historial, "CRNN · ajuste con recortes reales").figura(
    "figuras/curvas_crnn_real.png"
)
print(DiagnosticoDeSobreajuste(entrenador.historial).veredicto())
