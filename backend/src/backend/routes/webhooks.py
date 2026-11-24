"""Webhooks entrantes de Pey."""

import logging

from fastapi import APIRouter, Request

from backend.dependencies import ControladorCoDiDep, VerificadorDep
from backend.models.webhook import PagoQRRecibido

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/pey/codi", summary="Pago CoDi recibido")
async def pago_codi(
    peticion: Request,
    controlador: ControladorCoDiDep,
    verificador: VerificadorDep,
) -> dict[str, bool]:
    # La firma se verifica sobre los bytes crudos, antes de interpretarlos:
    # nada de este cuerpo es de fiar hasta que cuadre.
    crudo = await verificador.cuerpo_verificado(peticion)
    evento = PagoQRRecibido.model_validate_json(crudo)

    movido = controlador.registrar_pago(evento)
    if movido:
        log.info("Cobro %s pagado (transaccion %s)", evento.codiQrId, evento.transactionId)

    # Siempre 200. Un reintento de Pey sobre un cobro ya pagado no es un
    # error, y responder 4xx solo lograria que insista.
    return {"recibido": True, "aplicado": movido}
