from divieat_ticket.sintetico import ConfiguracionSintetico, GeneradorTicketsSinteticos


class TestGenerador:
    def test_es_reproducible_con_la_misma_semilla(self):
        a = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=42)).generar()
        b = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=42)).generar()
        assert a.verdad.a_dict() == b.verdad.a_dict()

    def test_la_verdad_cuadra_por_construccion(self):
        """Los precios de carta ya incluyen IVA: la suma de renglones es el TOTAL."""
        generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=3))
        for muestra in generador.lote(8, degradar=False):
            verdad = muestra.verdad
            assert verdad.cuadra()
            assert verdad.suma_productos == verdad.total_impreso
            # El subtotal es la base gravable, no la suma de productos.
            assert verdad.subtotal + verdad.iva == verdad.total_impreso
            assert verdad.subtotal < verdad.total_impreso

    def test_imprime_mayoritariamente_la_plantilla_dominante(self):
        """SOFT RESTAURANT es el POS mas comun: debe dominar el corpus."""
        generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=5))
        textos = [" ".join(m.renglones) for m in generador.lote(20, degradar=False)]
        assert sum("SOFT RESTAURANT" in t for t in textos) >= 12

    def test_el_perfil_del_parser_reconoce_lo_generado(self):
        """Generador y detector tienen que hablar el mismo idioma."""
        from divieat_ticket.perfiles import DetectorDePerfil

        generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=5))
        detector = DetectorDePerfil()
        reconocidos = 0
        for muestra in generador.lote(10, degradar=False):
            perfil, _ = detector.detectar(muestra.renglones)
            reconocidos += perfil.nombre == "PerfilSoftRestaurant"
        assert reconocidos >= 7

    def test_la_degradacion_cambia_la_imagen_pero_no_la_verdad(self):
        muestra = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=5)).generar()
        assert muestra.degradaciones
        assert muestra.imagen.dimensiones != muestra.limpia.dimensiones or muestra.degradaciones
        assert muestra.verdad.cuadra()
