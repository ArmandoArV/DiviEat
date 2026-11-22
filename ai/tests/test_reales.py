"""Alineacion de lecturas ruidosas contra la transcripcion exacta."""

import pytest

from divieat_ticket.modelo.reales import AlineadorDeSecuencias


class TestAlineador:
    def test_empareja_en_orden_pese_al_ruido(self):
        leidos = ["RESTALIANTE HARCELO", "MESA:2Y7", "1 BRDCOLI A LAS BRASAS 8160,00"]
        verdaderos = ["RESTAURANTE MARCELO", "MESA:2Y7", "1 BROCOLI A LAS BRASAS $160.00"]
        pares = AlineadorDeSecuencias().alinear(leidos, verdaderos)
        assert [p.texto_verdadero for p in pares] == verdaderos

    def test_tolera_renglones_que_el_ocr_no_leyo(self):
        """Un hueco en la lectura no debe desplazar el resto de las etiquetas."""
        leidos = ["CANT. DESCRIPCION", "1 COCA COLA 55.00", "1 STEAK SANDWICH 259.00"]
        verdaderos = [
            "CANT. DESCRIPCION", "1 COCA COLA $55.00",
            "1 CAZUELA WESTERN $225.00", "1 STEAK SANDWICH $259.00",
        ]
        pares = AlineadorDeSecuencias().alinear(leidos, verdaderos)
        emparejados = {p.indice_recorte: p.texto_verdadero for p in pares}
        assert emparejados[2] == "1 STEAK SANDWICH $259.00"
        assert "1 CAZUELA WESTERN $225.00" not in emparejados.values()

    def test_descarta_lo_que_no_se_parece(self):
        pares = AlineadorDeSecuencias().alinear(["XKCD 999"], ["1 COCA COLA $55.00"])
        assert pares == []

    def test_usa_el_orden_para_desambiguar_repetidos(self):
        """Dos «COCA COLA» con importes distintos: el orden decide cual es cual."""
        leidos = ["1 COCA COLA 5O.00", "1 FRESCA 5O.00", "1 COCA COLA LIGHT 5O.00"]
        verdaderos = ["1 COCA COLA $50.00", "1 FRESCA $50.00", "1 COCA COLA LIGHT $50.00"]
        pares = AlineadorDeSecuencias().alinear(leidos, verdaderos)
        assert [p.texto_verdadero for p in pares] == verdaderos

    @pytest.mark.parametrize("leidos, verdaderos", [([], ["A"]), (["A"], []), ([], [])])
    def test_listas_vacias(self, leidos, verdaderos):
        assert AlineadorDeSecuencias().alinear(leidos, verdaderos) == []
