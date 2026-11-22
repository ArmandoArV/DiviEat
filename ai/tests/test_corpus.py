"""El corpus de recortes del pipeline."""

from pathlib import Path

import numpy as np
import pytest
import torch

from divieat_ticket.modelo.alfabeto import Alfabeto
from divieat_ticket.modelo.corpus import ALTURA, CorpusDeRenglones, normalizar_recorte

CARPETA = Path("datos/corpus_pipeline")
sin_corpus = pytest.mark.skipif(
    not (CARPETA / "etiquetas.jsonl").is_file(),
    reason="corpus no construido (python construir_corpus.py)",
)


class TestNormalizacion:
    @pytest.mark.parametrize("alto, ancho", [(44, 600), (18, 120), (80, 1400)])
    def test_siempre_deja_32_px_de_alto(self, alto, ancho):
        recorte = normalizar_recorte(np.full((alto, ancho), 200, np.uint8))
        assert recorte.shape[0] == ALTURA
        assert 8 <= recorte.shape[1] <= 480

    def test_conserva_la_proporcion(self):
        recorte = normalizar_recorte(np.zeros((64, 320), np.uint8))
        assert recorte.shape[1] == pytest.approx(320 * ALTURA / 64, abs=1)


@sin_corpus
class TestCorpus:
    def test_la_particion_no_se_solapa(self):
        alfabeto = Alfabeto.de_tickets()
        entrenamiento = CorpusDeRenglones(CARPETA, alfabeto, hasta=0.88)
        validacion = CorpusDeRenglones(CARPETA, alfabeto, desde=0.88)
        nombres_entrenamiento = {r["imagen"] for r in entrenamiento.registros}
        nombres_validacion = {r["imagen"] for r in validacion.registros}
        assert nombres_entrenamiento and nombres_validacion
        assert not (nombres_entrenamiento & nombres_validacion)

    def test_las_muestras_salen_normalizadas(self):
        corpus = CorpusDeRenglones(CARPETA)
        tensor, codificado, texto = corpus[0]
        assert tensor.shape[0] == 1 and tensor.shape[1] == ALTURA
        assert tensor.min() >= 0.0 and tensor.max() <= 1.0   # tinta=1, papel=0
        assert texto and codificado.numel() == len(texto)
        assert torch.is_floating_point(tensor)
