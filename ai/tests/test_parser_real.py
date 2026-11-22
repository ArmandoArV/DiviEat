"""El parser medido contra tickets reales de Merida, Yucatan."""

import numpy as np
import pytest

from divieat_ticket.imagen import Imagen
from divieat_ticket.ocr import MotorDeReferencia
from divieat_ticket.parser import AnalizadorDeTicket, NormalizadorOCR

from fixtures_reales import TODOS

LIENZO = Imagen(np.zeros((10, 10), np.uint8))


def analizar(caso):
    analizador = AnalizadorDeTicket()
    ticket = analizador.analizar(MotorDeReferencia(caso.lineas).reconocer(LIENZO))
    return analizador, ticket


@pytest.mark.parametrize("caso", TODOS, ids=lambda c: c.nombre)
class TestTicketsReales:
    def test_detecta_el_pos(self, caso):
        analizador, _ = analizar(caso)
        assert analizador.ultimo_perfil.nombre == caso.pos

    def test_cuenta_los_productos(self, caso):
        _, ticket = analizar(caso)
        assert len(ticket.productos) == caso.productos_esperados

    def test_la_suma_cuadra_con_el_total_impreso(self, caso):
        _, ticket = analizar(caso)
        assert ticket.total_impreso.centavos == caso.total_esperado_centavos
        assert ticket.suma_productos.centavos == caso.total_esperado_centavos
        assert ticket.cuadra()

    def test_extrae_mesa_y_comensales(self, caso):
        _, ticket = analizar(caso)
        assert ticket.mesa == caso.mesa_esperada
        assert ticket.comensales == caso.comensales_esperados


class TestNormalizador:
    @pytest.mark.parametrize(
        "sucio, limpio",
        [
            ("T0TAL l,6SO.0O", "TOTAL 1,650.00"),
            ("l MICHELADA 9S.00", "1 MICHELADA 95.00"),
            ("4 ENCHILADAS VERDES 62O.OO", "4 ENCHILADAS VERDES 620.00"),
            ("MESA:2Y7", "MESA:2Y7"),
            ("FOLIO:122903", "FOLIO:122903"),
        ],
    )
    def test_corrige_segun_el_contexto(self, sucio, limpio):
        assert NormalizadorOCR().normalizar(sucio) == limpio
