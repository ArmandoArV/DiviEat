"""Pruebas del cobro CoDi: lo que protege dinero real.

No tocan la red ni Mongo. Lo que se verifica aqui es lo que, si falla en
silencio, cobra de mas o deja que un extraño marque una cuenta como pagada.
"""

import json
import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("PEY_WEBHOOK_SECRET", "whsec_" + "c2VjcmV0by1kZS1wcnVlYmE=")
os.environ.setdefault("PEY_API_KEY", "")

from fastapi.testclient import TestClient  # noqa: E402

import app as aplicacion  # noqa: E402
from backend.config import obtener_ajustes  # noqa: E402
from backend.controllers.codi import ControladorCoDi  # noqa: E402
from backend.classes.pey_client import ClientePey  # noqa: E402
from backend.dependencies import obtener_controlador_codi  # noqa: E402
from backend.models.codi import CobroGuardado  # noqa: E402
from backend.types.codi import EstadoCobro  # noqa: E402
from backend.utils.money import centavos_a_pesos, pesos_a_centavos  # noqa: E402
from standardwebhooks import Webhook  # noqa: E402


class RepositorioEnMemoria:
    """Doble del repositorio: las pruebas no deben necesitar un Mongo vivo.

    Ojo con la tentacion de lograr lo mismo haciendo que el repositorio real
    se trague los errores de Mongo: si la base no responde, el webhook TIENE
    que fallar fuerte para que Pey reintente. Tragarselo pierde el pago.
    """

    def __init__(self, cobros: list[CobroGuardado] | None = None) -> None:
        self.cobros = {c.id: c for c in (cobros or [])}

    def guardar(self, cobro: CobroGuardado) -> None:
        self.cobros[cobro.id] = cobro

    def obtener(self, id_cobro: str) -> CobroGuardado | None:
        return self.cobros.get(id_cobro)

    def por_orden(self, orden: str) -> list[CobroGuardado]:
        return [c for c in self.cobros.values() if c.orden == orden]

    def marcar_pagado(self, id_cobro: str, transaccion_id: str) -> bool:
        cobro = self.cobros.get(id_cobro)
        if cobro is None or cobro.estado is not EstadoCobro.PENDIENTE:
            return False
        cobro.estado = EstadoCobro.PAGADO
        cobro.transaccion_id = transaccion_id
        return True


def con_repositorio(repositorio: RepositorioEnMemoria) -> None:
    aplicacion.app.dependency_overrides[obtener_controlador_codi] = lambda: ControladorCoDi(
        cliente=ClientePey(api_key=""),
        repositorio=repositorio,
        ajustes=obtener_ajustes(),
    )


@pytest.fixture(autouse=True)
def _sin_mongo():
    yield
    aplicacion.app.dependency_overrides.clear()


def firmar(cuerpo: str) -> dict[str, str]:
    momento = datetime.now(timezone.utc)
    return {
        "content-type": "application/json",
        "webhook-id": "msg_1",
        "webhook-timestamp": str(int(momento.timestamp())),
        "webhook-signature": Webhook(os.environ["PEY_WEBHOOK_SECRET"]).sign(
            "msg_1", momento, cuerpo
        ),
    }


def cuerpo_de_pago(codi_qr_id: str = "qr-1") -> str:
    return json.dumps(
        {
            "type": "codi.qr.payment_received",
            "transactionId": "01M3",
            "codiQrId": codi_qr_id,
            "amount": 1,
            "metadata": {"externalMetadata": {"orden": "2471", "comensal": "mariana"}},
        }
    )


cliente = TestClient(aplicacion.app)


def test_salud_responde_aunque_no_haya_mongo_ni_llave():
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["pey_configurado"] is False


def test_sin_llave_el_cobro_falla_claro_y_no_con_un_500():
    respuesta = cliente.post(
        "/codi/cobros",
        json={"orden": "2471", "comensal": "mariana", "centavos": 1},
    )
    assert respuesta.status_code == 503
    assert "PEY_API_KEY" in respuesta.json()["error"]


def test_el_webhook_rechaza_lo_que_no_viene_firmado():
    """Sin esto, cualquiera que sepa la URL marca cuentas como pagadas."""
    respuesta = cliente.post(
        "/webhooks/pey/codi",
        json={
            "type": "codi.qr.payment_received",
            "transactionId": "01M3",
            "codiQrId": "35a1",
            "amount": 150,
        },
    )
    assert respuesta.status_code == 401


def test_el_webhook_con_firma_valida_marca_el_cobro_pagado():
    pendiente = CobroGuardado(
        id="qr-1", orden="2471", comensal="mariana", centavos=100,
        estado=EstadoCobro.PENDIENTE, qr_cadena="...", num_ref="2471",
        creado_en=datetime.now(timezone.utc),
    )
    repositorio = RepositorioEnMemoria([pendiente])
    con_repositorio(repositorio)

    cuerpo = cuerpo_de_pago("qr-1")
    respuesta = cliente.post("/webhooks/pey/codi", content=cuerpo, headers=firmar(cuerpo))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"recibido": True, "aplicado": True}
    assert repositorio.cobros["qr-1"].estado is EstadoCobro.PAGADO


def test_un_reintento_de_pey_no_vuelve_a_cobrar():
    """Pey reintenta. El segundo golpe no debe mover nada ni devolver error."""
    pendiente = CobroGuardado(
        id="qr-1", orden="2471", comensal="mariana", centavos=100,
        estado=EstadoCobro.PENDIENTE, qr_cadena="...", num_ref="2471",
        creado_en=datetime.now(timezone.utc),
    )
    repositorio = RepositorioEnMemoria([pendiente])
    con_repositorio(repositorio)
    cuerpo = cuerpo_de_pago("qr-1")

    primera = cliente.post("/webhooks/pey/codi", content=cuerpo, headers=firmar(cuerpo))
    segunda = cliente.post("/webhooks/pey/codi", content=cuerpo, headers=firmar(cuerpo))

    assert primera.json()["aplicado"] is True
    assert segunda.status_code == 200, "un reintento no es un error"
    assert segunda.json()["aplicado"] is False, "no debe volver a aplicarse"


@pytest.mark.parametrize(
    "centavos,pesos",
    [(1, "0.01"), (27600, "276.00"), (12050, "120.50"), (124000, "1240.00")],
)
def test_centavos_a_pesos_es_exacto(centavos, pesos):
    """Pey cobra en PESOS; el dominio guarda CENTAVOS. Aqui se cruzan."""
    assert str(centavos_a_pesos(centavos)) == pesos


def test_el_viaje_de_ida_y_vuelta_no_pierde_centavos():
    for centavos in (1, 99, 100, 12050, 124000):
        assert pesos_a_centavos(centavos_a_pesos(centavos)) == centavos


def test_el_modo_de_prueba_frena_un_cobro_grande():
    """Pey no tiene sandbox: esto cobra de verdad.

    Un monto grande con el modo de prueba encendido es casi siempre un error
    de unidades —centavos donde iban pesos— y eso serian 100x de mas. El
    freno salta antes de siquiera llamar a Pey.
    """
    con_repositorio(RepositorioEnMemoria())
    respuesta = cliente.post(
        "/codi/cobros",
        json={"orden": "2471", "comensal": "mariana", "centavos": 27600},
    )
    assert respuesta.status_code == 422
    assert "276.00" in respuesta.json()["error"]


def test_bajo_el_tope_el_modo_de_prueba_deja_pasar():
    """Un centavo pasa el freno y entonces si se queja de que falta la llave."""
    con_repositorio(RepositorioEnMemoria())
    respuesta = cliente.post(
        "/codi/cobros",
        json={"orden": "2471", "comensal": "mariana", "centavos": 1},
    )
    assert respuesta.status_code == 503, "ya no es el monto, es la llave"


def test_el_importe_tiene_que_ser_positivo():
    con_repositorio(RepositorioEnMemoria())
    respuesta = cliente.post(
        "/codi/cobros",
        json={"orden": "2471", "comensal": "mariana", "centavos": 0},
    )
    assert respuesta.status_code == 422
