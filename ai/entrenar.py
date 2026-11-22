"""Script de entrenamiento de la CRNN (uso: .venv/bin/python entrenar.py)."""
import sys
from pathlib import Path

sys.path.insert(0, "src")

from divieat_ticket.modelo.entrenamiento import ConfiguracionEntrenamiento, EntrenadorCRNN

config = ConfiguracionEntrenamiento(
    epocas=12,
    tamano_lote=32,
    muestras_entrenamiento=10_000,
    muestras_validacion=800,
    tasa_aprendizaje=3e-4,
    ruta_checkpoint=Path("modelos/crnn.pt"),
)
entrenador = EntrenadorCRNN(config=config)
print(f"dispositivo: {entrenador.dispositivo} · {entrenador.modelo.parametros_entrenables:,} parametros")
print(f"alfabeto: {entrenador.alfabeto}", flush=True)
entrenador.entrenar()

print("\nejemplos (predicho | verdadero):")
for predicho, verdadero in entrenador.ejemplos(8):
    marca = "ok " if predicho == verdadero else "dif"
    print(f"  [{marca}] {predicho!r}\n        {verdadero!r}")
