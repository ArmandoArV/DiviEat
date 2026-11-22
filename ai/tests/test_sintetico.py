from divieat_ticket.sintetico import ConfiguracionSintetico, GeneradorTicketsSinteticos


class TestGenerador:
    def test_es_reproducible_con_la_misma_semilla(self):
        a = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=42)).generar()
        b = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=42)).generar()
        assert a.verdad.a_dict() == b.verdad.a_dict()

    def test_la_verdad_cuadra_por_construccion(self):
        generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=3))
        for muestra in generador.lote(8, degradar=False):
            assert muestra.verdad.cuadra()
            assert muestra.verdad.suma_productos == muestra.verdad.subtotal

    def test_la_degradacion_cambia_la_imagen_pero_no_la_verdad(self):
        muestra = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=5)).generar()
        assert muestra.degradaciones
        assert muestra.imagen.dimensiones != muestra.limpia.dimensiones or muestra.degradaciones
        assert muestra.verdad.cuadra()
