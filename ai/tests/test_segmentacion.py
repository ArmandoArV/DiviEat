"""La U-Net de renglones y las mascaras que la supervisan."""

import cv2
import numpy as np
import pytest
import torch

from divieat_ticket.modelo.segmentacion import (
    ALTO_ENTRADA, ANCHO_ENTRADA, PerdidaDeSegmentacion, SegmentadorNeuronal, UNet,
    interseccion_sobre_union,
)
from divieat_ticket.sintetico import mascara_de_renglones


class TestMascaras:
    def test_los_renglones_contiguos_no_se_tocan(self):
        """El encogimiento vertical es lo que garantiza componentes separadas."""
        cajas = [(10, y, 300, 30) for y in range(0, 300, 32)]   # renglones casi pegados
        mascara = mascara_de_renglones((320, 400), cajas)
        componentes, _ = cv2.connectedComponents((mascara > 127).astype(np.uint8))
        assert componentes - 1 == len(cajas)

    def test_la_banda_cubre_todo_el_ancho_del_renglon(self):
        """Descripcion e importe deben caer en la misma componente."""
        mascara = mascara_de_renglones((100, 800), [(20, 40, 700, 30)])
        fila = mascara[55]
        assert fila[20] == 255 and fila[700] == 255
        componentes, _ = cv2.connectedComponents((mascara > 127).astype(np.uint8))
        assert componentes - 1 == 1

    def test_ignora_cajas_degeneradas(self):
        mascara = mascara_de_renglones((50, 50), [(0, 0, 10, 1)])
        assert mascara.max() == 255        # altura minima, pero pinta algo


class TestRed:
    def test_conserva_el_tamano_de_entrada(self):
        salida = UNet(base=4)(torch.zeros(1, 1, 128, 96))
        assert salida.shape == (1, 1, 128, 96)

    def test_la_resolucion_de_trabajo_es_divisible_por_16(self):
        """Cuatro reducciones a la mitad: si no divide, los saltos no casan."""
        assert ALTO_ENTRADA % 16 == 0 and ANCHO_ENTRADA % 16 == 0

    def test_la_perdida_premia_la_coincidencia(self):
        objetivo = torch.zeros(1, 1, 32, 32)
        objetivo[:, :, 8:24, :] = 1.0
        perdida = PerdidaDeSegmentacion()
        buena = perdida(torch.where(objetivo > 0, 8.0, -8.0), objetivo)
        mala = perdida(torch.where(objetivo > 0, -8.0, 8.0), objetivo)
        assert buena < mala

    def test_iou_perfecto_e_inverso(self):
        objetivo = torch.zeros(1, 1, 16, 16)
        objetivo[:, :, :8, :] = 1.0
        assert interseccion_sobre_union(torch.where(objetivo > 0, 8.0, -8.0), objetivo) == 1.0
        assert interseccion_sobre_union(torch.where(objetivo > 0, -8.0, 8.0), objetivo) == 0.0


class TestEscalado:
    def test_deshace_el_encogimiento_al_volver_al_original(self):
        """La caja predicha es el nucleo; hay que devolverle su altura real."""
        caja = SegmentadorNeuronal._a_original(
            x=10, y=100, ancho=200, alto=10, escala_x=2.0, escala_y=2.0,
            alto_original=2000, ancho_original=1000,
        )
        assert caja.alto == pytest.approx(10 * 2.0 / 0.5, abs=1)
        assert caja.centro_y == pytest.approx((100 + 5) * 2.0, abs=1)

    def test_no_se_sale_de_la_imagen(self):
        caja = SegmentadorNeuronal._a_original(
            x=0, y=0, ancho=50, alto=20, escala_x=1.0, escala_y=1.0,
            alto_original=30, ancho_original=60,
        )
        assert caja.y >= 0 and caja.y + caja.alto <= 30
