"""¿La textura termica cierra el salto a fotos reales?

Se entrena la CRNN base solo con renglones sinteticos —ahora con textura de
impresora termica— y se mide directamente sobre los recortes reales, **sin
afinar con ellos**. Si el renderizador se acerca al papel real, el CER tiene
que bajar respecto al 1.12 del modelo anterior.
"""
import sys
from pathlib import Path
sys.path.insert(0, "src")

import torch
from torch.utils.data import DataLoader

from divieat_ticket.modelo.corpus import CorpusDeRenglones
from divieat_ticket.modelo.ctc import DecodificadorVoraz
from divieat_ticket.modelo.datos import agrupar_lote
from divieat_ticket.modelo.entrenamiento import ConfiguracionEntrenamiento, EntrenadorCRNN
from divieat_ticket.modelo.graficas import GraficadorDeAprendizaje
from divieat_ticket.modelo.metricas import TasaDeError


def medir_en_reales(entrenador):
    corpus = CorpusDeRenglones("datos/corpus_reales", entrenador.alfabeto)
    cargador = DataLoader(corpus, batch_size=16, collate_fn=agrupar_lote)
    decodificador = DecodificadorVoraz(entrenador.alfabeto)
    predichos, verdaderos = [], []
    entrenador.modelo.eval()
    with torch.no_grad():
        for imagenes, _, _, textos in cargador:
            predichos.extend(decodificador.decodificar(
                entrenador.modelo(imagenes.to(entrenador.dispositivo)).cpu()))
            verdaderos.extend(textos)
    exactos = sum(p == v for p, v in zip(predichos, verdaderos))
    return TasaDeError().medir(predichos, verdaderos).tasa, exactos, len(verdaderos), predichos, verdaderos


entrenador = EntrenadorCRNN(config=ConfiguracionEntrenamiento(
    epocas=16, muestras_entrenamiento=12_000, muestras_validacion=800,
    tasa_aprendizaje=3e-4, ruta_checkpoint=Path("modelos/crnn_termico.pt"),
))
print(f"dispositivo: {entrenador.dispositivo}", flush=True)
cer, exactos, total, _, _ = medir_en_reales(entrenador)
print(f"ANTES de entrenar · CER real {cer:.4f} · exactos {exactos}/{total}", flush=True)

entrenador.entrenar()
GraficadorDeAprendizaje(entrenador.historial, "CRNN · renglones con textura termica").figura(
    "figuras/curvas_crnn_termico.png"
)

cer, exactos, total, predichos, verdaderos = medir_en_reales(entrenador)
print(f"\nDESPUES · CER sobre {total} recortes REALES: {cer:.4f} · exactos {exactos}/{total}")
print("\nejemplos:")
for p, v in list(zip(predichos, verdaderos))[20:28]:
    print(f"  esperado {v!r}\n  leido    {p!r}")
