"""Curvas de aprendizaje: datos escasos vs datos amplios.

Unica variable que cambia entre los dos entrenamientos: cuantas muestras ve la
red. Todo lo demas (arquitectura, optimizador, tasa, conjunto de validacion)
se mantiene fijo, asi que la diferencia entre las curvas es atribuible al
tamano del conjunto.
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

from divieat_ticket.modelo.entrenamiento import ConfiguracionEntrenamiento, EntrenadorCRNN
from divieat_ticket.modelo.graficas import (
    ComparadorDeCurvas, DiagnosticoDeSobreajuste, GraficadorDeAprendizaje,
)

EXPERIMENTOS = {
    "400 muestras": ConfiguracionEntrenamiento(
        epocas=12, muestras_entrenamiento=400, muestras_validacion=600,
        paciencia=99, ruta_checkpoint=Path("modelos/_escaso.pt"),
    ),
    "2500 muestras": ConfiguracionEntrenamiento(
        epocas=8, muestras_entrenamiento=2500, muestras_validacion=600,
        paciencia=99, ruta_checkpoint=Path("modelos/_amplio.pt"),
    ),
}

historiales = {}
for nombre, config in EXPERIMENTOS.items():
    print(f"\n===== {nombre} =====", flush=True)
    entrenador = EntrenadorCRNN(config=config)
    historiales[nombre] = entrenador.entrenar()
    ruta = GraficadorDeAprendizaje(historiales[nombre], f"CRNN · {nombre}").figura(
        Path("figuras") / f"curvas_{nombre.split()[0]}.png"
    )
    print(f"figura: {ruta}")
    print(DiagnosticoDeSobreajuste(historiales[nombre]).veredicto(), flush=True)

comparador = ComparadorDeCurvas(historiales)
print("\n" + comparador.tabla())
print("comparativa:", comparador.figura(
    "figuras/comparativa_sobreajuste.png", "Efecto del tamano del conjunto de entrenamiento"
))
