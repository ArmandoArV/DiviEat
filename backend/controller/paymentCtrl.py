from fastapi.responses import JSONResponse

from schemas.paymentLink import PaymentLinkBody
from schemas.qr import QrBody
from services import paymentService as PaymentService


def crear_qr(body: QrBody):
    try:
        return PaymentService.generar_qr_codi(body)
    except Exception as err:
        return JSONResponse(status_code=502, content={"error": str(err)})


def crear_link_pago(body: PaymentLinkBody):
    try:
        return PaymentService.generar_link_pago(body)
    except Exception as err:
        return JSONResponse(status_code=502, content={"error": str(err)})