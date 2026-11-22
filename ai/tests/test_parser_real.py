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


class TestCorreccionPorCuadre:
    """El ticket se verifica a si mismo: el OCR confunde `$` con 8 o 5."""

    def _marcelo_mal_leido(self):
        from divieat_ticket.dominio import Dinero, Producto, TicketExtraido

        return TicketExtraido(
            productos=[
                Producto("BROCOLI A LAS BRASAS", 1, Dinero(816000)),   # $160.00
                Producto("LIMONADA NATURAL", 1, Dinero(85000)),        # $50.00
                Producto("COCA COLA", 1, Dinero(85000)),               # $50.00
                Producto("FRESCA", 1, Dinero(5000)),
                Producto("COCA COLA LIGHT", 1, Dinero(5000)),
                Producto("AMSTEL ULTRA", 1, Dinero(7000)),
                Producto("CHAPATA ARRACHERA", 3, Dinero(60000)),
                Producto("LATTE DE SABOR FRIO", 1, Dinero(87000)),     # $70.00
                Producto("DIRTY CHAI EN LAS R", 1, Dinero(7500)),
            ],
            total_impreso=Dinero(117500),
        )

    def test_repara_los_importes_que_cuadran(self):
        from divieat_ticket.parser import CorrectorDeImportes

        ticket = self._marcelo_mal_leido()
        assert not ticket.cuadra()
        assert CorrectorDeImportes().corregir(ticket) == 4
        assert ticket.cuadra()
        assert ticket.suma_productos.centavos == 117500

    def test_marca_como_dudoso_lo_que_corrigio(self):
        from divieat_ticket.parser import CorrectorDeImportes

        ticket = self._marcelo_mal_leido()
        CorrectorDeImportes().corregir(ticket)
        assert len(ticket.productos_dudosos()) == 4

    def test_no_toca_un_ticket_que_ya_cuadra(self):
        from divieat_ticket.dominio import Dinero, Producto, TicketExtraido
        from divieat_ticket.parser import CorrectorDeImportes

        ticket = TicketExtraido(
            productos=[Producto("MENU", 1, Dinero(50000))], total_impreso=Dinero(50000)
        )
        assert CorrectorDeImportes().corregir(ticket) == 0

    def test_no_adivina_cuando_hay_varias_soluciones(self):
        """Dos productos identicos mal leidos: cualquiera de los dos cuadraria."""
        from divieat_ticket.dominio import Dinero, Producto, TicketExtraido
        from divieat_ticket.parser import CorrectorDeImportes

        ticket = TicketExtraido(
            productos=[Producto("A", 1, Dinero(85000)), Producto("B", 1, Dinero(85000))],
            total_impreso=Dinero(90000),      # 850 + 50  o  50 + 850
        )
        assert CorrectorDeImportes().corregir(ticket) == 0
        assert not ticket.cuadra()

    def test_repara_el_total_con_subtotal_mas_iva(self):
        from divieat_ticket.dominio import Dinero, TicketExtraido
        from divieat_ticket.parser import CorrectorDeImportes

        ticket = TicketExtraido(
            subtotal=Dinero(101293), iva=Dinero(16207), total_impreso=Dinero(5117500)
        )
        assert CorrectorDeImportes().corregir_total(ticket)
        assert ticket.total_impreso == Dinero(117500)

    def test_no_sustituye_el_total_si_nada_coincide(self):
        """Si subtotal o IVA tambien se leyeron mal, no hay a que agarrarse."""
        from divieat_ticket.dominio import Dinero, TicketExtraido
        from divieat_ticket.parser import CorrectorDeImportes

        ticket = TicketExtraido(
            subtotal=Dinero(76379), iva=Dinero(5821), total_impreso=Dinero(542200)
        )
        assert not CorrectorDeImportes().corregir_total(ticket)
        assert ticket.total_impreso == Dinero(542200)
