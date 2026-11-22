import torch

from divieat_ticket.modelo.alfabeto import Alfabeto
from divieat_ticket.modelo.crnn import CRNN
from divieat_ticket.modelo.ctc import DecodificadorVoraz
from divieat_ticket.modelo.datos import ConjuntoLineas, agrupar_lote
from divieat_ticket.modelo.metricas import TasaDeError, distancia_de_edicion


class TestAlfabeto:
    def test_reserva_el_indice_cero_para_el_blanco(self):
        alfabeto = Alfabeto.de_tickets()
        assert alfabeto.BLANCO == 0
        assert len(alfabeto) == len(alfabeto.caracteres) + 1
        assert 0 not in alfabeto.codificar(alfabeto.caracteres)

    def test_ida_y_vuelta(self):
        alfabeto = Alfabeto.de_tickets()
        texto = "TOTAL: $1,650.00"
        assert alfabeto.decodificar(alfabeto.codificar(texto)) == texto

    def test_descarta_lo_no_representable(self):
        alfabeto = Alfabeto("ABC")
        assert alfabeto.limpiar("ABCDEF") == "ABC"


class TestDecodificadorCTC:
    def test_colapsa_repeticiones_antes_de_quitar_blancos(self):
        """GALLO: las dos L estan separadas por un blanco y deben sobrevivir."""
        alfabeto = Alfabeto("GALO")
        decodificador = DecodificadorVoraz(alfabeto)
        indices = [i + 1 for i in [0, 1]] + [2, 2, 0, 2, 2] + [4]  # G A L L _ L L O
        assert decodificador._colapsar([1, 1, 2, 3, 3, 0, 3, 4]) == [1, 2, 3, 3, 4]

    def test_decodifica_un_lote(self):
        alfabeto = Alfabeto.de_tickets()
        log_probabilidades = torch.log_softmax(torch.randn(12, 3, len(alfabeto)), dim=2)
        textos = DecodificadorVoraz(alfabeto).decodificar(log_probabilidades)
        assert len(textos) == 3


class TestMetricas:
    def test_distancia_de_edicion(self):
        assert distancia_de_edicion("TOTAL", "TOTAL") == 0
        assert distancia_de_edicion("165O.00", "1650.00") == 1
        assert distancia_de_edicion("", "ABC") == 3

    def test_cer(self):
        resultado = TasaDeError().medir(["165O.00"], ["1650.00"])
        assert resultado.errores == 1
        assert resultado.referencia == 7


class TestRedYDatos:
    def test_la_altura_colapsa_a_un_paso_por_columna(self):
        red = CRNN(clases=40)
        salida = red(torch.zeros(2, 1, 32, 256))
        assert salida.shape[1:] == (2, 40)
        assert salida.shape[0] == red.longitud_de_salida(256)

    def test_el_lote_se_rellena_al_ancho_maximo(self):
        conjunto = ConjuntoLineas(4)
        imagenes, objetivos, longitudes, textos = agrupar_lote([conjunto[i] for i in range(4)])
        assert imagenes.shape[0] == 4 and imagenes.shape[2] == 32
        assert int(longitudes.sum()) == objetivos.numel()
        assert len(textos) == 4

    def test_las_muestras_son_reproducibles(self):
        a = ConjuntoLineas(3)[1]
        b = ConjuntoLineas(3)[1]
        assert a[2] == b[2]
        assert torch.equal(a[0], b[0])
