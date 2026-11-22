"""Caso forzado de sobreajuste: conjunto diminuto y sin aumentacion.

Con 150 renglones fijos y sin degradacion, la red puede memorizar las imagenes
exactas. La validacion usa textos que nunca vio, asi que su perdida repunta en
cuanto la memorizacion sustituye al aprendizaje. Es el caso positivo que falta
para poder contrastar el diagnostico.
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

from divieat_ticket.modelo.datos import ConfiguracionLineas
from divieat_ticket.modelo.entrenamiento import ConfiguracionEntrenamiento, EntrenadorCRNN
from divieat_ticket.modelo.graficas import DiagnosticoDeSobreajuste, GraficadorDeAprendizaje

config = ConfiguracionEntrenamiento(
    epocas=26,
    muestras_entrenamiento=150,
    muestras_validacion=300,
    tasa_aprendizaje=8e-4,
    paciencia=99,
    ruta_checkpoint=Path("modelos/_memoriza.pt"),
    datos=ConfiguracionLineas(probabilidad_degradar=0.0),
)
entrenador = EntrenadorCRNN(config=config)
print("150 muestras fijas, sin degradacion -> la red puede memorizarlas", flush=True)
historial = entrenador.entrenar()

ruta = GraficadorDeAprendizaje(historial, "CRNN · 150 muestras sin aumentacion").figura(
    "figuras/curvas_memorizacion.png"
)
print(f"\nfigura: {ruta}")
print(DiagnosticoDeSobreajuste(historial).veredicto())

import json
Path("figuras/historial_memorizacion.json").write_text(
    json.dumps([vars(r) for r in historial], indent=2), encoding="utf-8"
)
