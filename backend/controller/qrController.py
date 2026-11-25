from fastapi.responses import JSONResponse

from schemas.qr import QrBody
from services import qrService as QrService


def crear_qr(body: QrBody):
    try:
        return QrService.generar_qr_codi(body)
    except Exception as err:
        return JSONResponse(status_code=502, content={"error": str(err)})