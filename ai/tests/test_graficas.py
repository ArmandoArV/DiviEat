"""El diagnostico de sobreajuste, probado con curvas sinteticas de libro."""

import pytest

from divieat_ticket.modelo.entrenamiento import RegistroEpoca
from divieat_ticket.modelo.graficas import ComparadorDeCurvas, DiagnosticoDeSobreajuste


def curva(perdidas_entrenamiento, perdidas_validacion):
    return [
        RegistroEpoca(
            epoca=i + 1,
            perdida_entrenamiento=pe,
            perdida_validacion=pv,
            cer_entrenamiento=max(0.0, pe / 10),
            cer_validacion=max(0.0, pv / 10),
            segundos=1.0,
        )
        for i, (pe, pv) in enumerate(zip(perdidas_entrenamiento, perdidas_validacion))
    ]


class TestDiagnostico:
    def test_detecta_sobreajuste_cuando_la_validacion_repunta(self):
        historial = curva([3.0, 1.5, 0.6, 0.2, 0.05], [3.1, 1.7, 0.9, 1.3, 1.9])
        veredicto = DiagnosticoDeSobreajuste(historial).veredicto()
        assert veredicto.etiqueta == "sobreajuste"
        assert veredicto.epoca_optima == 3
        assert veredicto.repunte > 0

    def test_buen_ajuste_cuando_las_curvas_bajan_juntas(self):
        historial = curva([3.0, 1.2, 0.5, 0.2, 0.1], [3.1, 1.3, 0.55, 0.24, 0.12])
        veredicto = DiagnosticoDeSobreajuste(historial).veredicto()
        assert veredicto.etiqueta == "buen ajuste"
        assert veredicto.epoca_optima == len(historial)

    def test_detecta_subajuste_cuando_todo_sigue_alto(self):
        historial = curva([6.0, 5.4, 5.0], [6.1, 5.5, 5.1])
        assert DiagnosticoDeSobreajuste(historial).veredicto().etiqueta == "subajuste"

    def test_sobreajuste_leve_por_brecha_sin_repunte(self):
        historial = curva([2.0, 0.9, 0.30, 0.10], [2.1, 1.1, 0.70, 0.60])
        assert DiagnosticoDeSobreajuste(historial).veredicto().etiqueta == "sobreajuste leve"

    def test_historial_vacio_falla(self):
        with pytest.raises(ValueError):
            DiagnosticoDeSobreajuste([])


class TestFiguras:
    def test_escribe_la_figura(self, tmp_path):
        from divieat_ticket.modelo.graficas import GraficadorDeAprendizaje

        historial = curva([3.0, 1.2, 0.5], [3.1, 1.3, 0.6])
        ruta = GraficadorDeAprendizaje(historial, "prueba").figura(tmp_path / "c.png")
        assert ruta.is_file() and ruta.stat().st_size > 1000

    def test_tabla_comparativa(self):
        tabla = ComparadorDeCurvas(
            {"escaso": curva([2.0, 0.5, 0.1], [2.1, 0.8, 1.4]),
             "amplio": curva([2.0, 0.6, 0.2], [2.1, 0.65, 0.22])}
        ).tabla()
        assert "sobreajuste" in tabla and "buen ajuste" in tabla
