from fastapi import APIRouter

from controller import paymentCtrl as PaymentCtrl
from schemas.paymentLink import PaymentLinkRespuesta
from schemas.qr import QrRespuesta


v1_router = APIRouter(prefix="/v1/payment", tags=["Payment"])

v1_router.add_api_route(
    "/qrcode", PaymentCtrl.crear_qr, methods=["POST"], status_code=201, response_model=QrRespuesta
)

v1_router.add_api_route(
    "/paylink", PaymentCtrl.crear_link_pago, methods=["POST"], status_code=201, response_model=PaymentLinkRespuesta
)