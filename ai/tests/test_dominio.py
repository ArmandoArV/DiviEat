import pytest

from divieat_ticket.dominio import Dinero, ErrorDeDominio, Producto, TicketExtraido


class TestDinero:
    @pytest.mark.parametrize(
        "texto, centavos",
        [
            ("$1,240.00", 124000),
            ("1.240,00", 124000),
            ("240", 24000),
            ("$ 95.50", 9550),
            ("TOTAL: $1,650.00", 165000),
            ("1 240.00", 124000),
            ("$422.00", 42200),
        ],
    )
    def test_lee_formatos_de_ticket(self, texto, centavos):
        assert Dinero.desde_texto(texto) == Dinero(centavos)

    def test_sin_importe_devuelve_none(self):
        assert Dinero.desde_texto("GRACIAS POR SU VISITA") is None

    def test_no_acumula_error_de_flotante(self):
        diez_centavos = Dinero(10)
        assert sum((diez_centavos for _ in range(10)), Dinero(0)) == Dinero(100)

    def test_multiplicar_por_flotante_falla(self):
        with pytest.raises(ErrorDeDominio):
            Dinero(100) * 1.5


class TestProducto:
    def test_deriva_unitario_exacto(self):
        producto = Producto("TACOS DE PASTOR", 4, Dinero(24000))
        assert producto.precio_unitario == Dinero(6000)
        assert producto.unitario_cuadra

    def test_no_inventa_unitario_cuando_no_divide(self):
        producto = Producto("GOHAN", 3, Dinero(10000))
        assert producto.precio_unitario is None

    def test_marca_dudoso_si_el_unitario_no_cuadra(self):
        producto = Producto("ROLLO", 2, Dinero(25000), precio_unitario=Dinero(100000))
        assert producto.es_dudoso()


class TestCuadre:
    def test_cuadra_contra_total_no_contra_subtotal(self):
        """En Mexico el precio incluye IVA: subtotal es la base pre-impuesto."""
        ticket = TicketExtraido(
            productos=[Producto("CHAPATA", 3, Dinero(60000)), Producto("COCA", 1, Dinero(57500))],
            subtotal=Dinero(101293),
            iva=Dinero(16207),
            total_impreso=Dinero(117500),
        )
        assert ticket.suma_productos == Dinero(117500)
        assert ticket.total_de_referencia == Dinero(117500)
        assert ticket.cuadra()

    def test_descuenta_propina_incluida_en_el_total(self):
        ticket = TicketExtraido(
            productos=[Producto("MENU", 1, Dinero(100000))],
            propina=Dinero(15000),
            total_impreso=Dinero(115000),
        )
        assert ticket.cuadra()

    def test_sin_total_legible_no_afirma_que_cuadra(self):
        ticket = TicketExtraido(productos=[Producto("MENU", 1, Dinero(100000))])
        assert not ticket.cuadra()
        assert ticket.diferencia() is None
