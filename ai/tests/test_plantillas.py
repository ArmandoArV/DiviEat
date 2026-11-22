"""Las plantillas de impresion, contra los tickets reales que las inspiran."""

import random

import pytest

from divieat_ticket.dominio import Dinero, Producto, TicketExtraido
from divieat_ticket.plantillas import (
    CatalogoDePlantillas, ContextoDeTicket, NumeroEnLetras, PlantillaSoftRestaurant,
)


class TestNumeroEnLetras:
    @pytest.mark.parametrize(
        "centavos, frase",
        [
            # Las cuatro frases vienen de tickets reales de Merida y Cuernavaca.
            (117500, "UN MIL CIENTO SETENTA Y CINCO PESOS 00/100 M.N."),
            (42200, "CUATROCIENTOS VEINTIDOS PESOS 00/100 M.N."),
            (165000, "UN MIL SEISCIENTOS CINCUENTA PESOS 00/100 M.N."),
            (136000, "UN MIL TRESCIENTOS SESENTA PESOS 00/100 M.N."),
            (10000, "CIEN PESOS 00/100 M.N."),
            (0, "CERO PESOS 00/100 M.N."),
        ],
    )
    def test_reproduce_las_frases_impresas(self, centavos, frase):
        assert NumeroEnLetras().convertir(Dinero(centavos)) == frase


class TestPlantillaSoftRestaurant:
    def _ticket(self):
        productos = [
            Producto("BROCOLI A LAS BRASAS", 1, Dinero(16000)),
            Producto("CHAPATA ARRACHERA", 3, Dinero(60000)),
        ]
        total = Dinero.suma(p.importe for p in productos)
        base = Dinero(int(round(total.centavos / 1.16)))
        return TicketExtraido(
            productos=productos, restaurante="RESTAURANTE MARCELO", folio="122903",
            subtotal=base, iva=total - base, total_impreso=total,
        )

    def _contexto(self):
        from datetime import datetime

        return ContextoDeTicket(
            nombre="RESTAURANTE MARCELO",
            direccion="C. 6 400, LAS AMERICAS LOCAL 15 MERIDA YUCATAN MEXICO CP 97302",
            mesa="2Y7", mesero="MAHOL", comensales=5, orden=154,
            apertura=datetime(2026, 10, 23, 20, 34, 7),
            cierre=datetime(2026, 10, 23, 21, 53, 52),
            version_pos="12",
        )

    def _textos(self, ancho=44):
        from divieat_ticket.sintetico import EstiloDeImporte

        plantilla = PlantillaSoftRestaurant(random.Random(0))
        renglones = plantilla.componer(
            self._ticket(), self._contexto(), EstiloDeImporte(EstiloDeImporte.PEGADO), ancho
        )
        return [texto for texto, _, _ in renglones]

    def test_imprime_las_marcas_del_pos(self):
        texto = "\n".join(self._textos())
        for marca in ["MESA:2Y7", "MESERO:MAHOL", "FOLIO:122903", "CANT. DESCRIPCION",
                      "TOTAL:", "SON:", "SOFT RESTAURANT V12 PRO"]:
            assert marca in texto, marca

    def test_usa_el_reloj_de_12_horas(self):
        texto = "\n".join(self._textos())
        assert "23/10/2026 08:34:07 PM" in texto
        assert "23/10/2026 09:53:52 PM" in texto

    def test_corta_la_direccion_a_mitad_de_palabra(self):
        """Los tickets reales parten por ancho de papel, no por palabras."""
        textos = self._textos(ancho=44)
        direccion = [t for t in textos if t.startswith("C. 6 400")]
        assert direccion and len(direccion[0]) == 44

    def test_el_detector_reconoce_su_propia_plantilla(self):
        from divieat_ticket.perfiles import DetectorDePerfil

        perfil, puntaje = DetectorDePerfil().detectar(self._textos())
        assert perfil.nombre == "PerfilSoftRestaurant"
        assert puntaje > 0.5


class TestCatalogo:
    def test_predomina_soft_restaurant(self):
        catalogo = CatalogoDePlantillas(random.Random(1), peso_soft=0.75)
        elegidas = [catalogo.elegir().nombre for _ in range(200)]
        proporcion = elegidas.count("PlantillaSoftRestaurant") / len(elegidas)
        assert 0.65 < proporcion < 0.85
