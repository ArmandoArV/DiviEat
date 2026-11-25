from fastapi import APIRouter

from controller import qrController as QrCtrl
from schemas.qr import QrRespuesta

router = APIRouter(prefix="/api/qr", tags=["QR"])

router.add_api_route(
    "", QrCtrl.crear_qr, methods=["POST"], status_code=201, response_model=QrRespuesta
)