import http.client
import json
import os

from dotenv import load_dotenv

from schemas.paymentLink import PaymentLinkBody, PaymentLinkRespuesta
from schemas.qr import QrBody, QrRespuesta

load_dotenv()


def _post_pey(path: str, payload: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {os.getenv('PEY_API_TOKEN')}",
    }

    conn = http.client.HTTPSConnection(os.getenv("PEY_HOST"), timeout=10)
    try:
        conn.request("POST", path, payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
    finally:
        conn.close()

    if res.status >= 400:
        raise Exception(f"Pey respondio {res.status}: {data}")
    return data


def generar_qr_codi(body: QrBody) -> QrRespuesta:
    return QrRespuesta.model_validate_json(
        _post_pey("/codi/qr", body.model_dump_json(exclude_none=True))
    )


def generar_link_pago(body: PaymentLinkBody) -> PaymentLinkRespuesta:
    payload = body.model_dump(exclude={"concept", "numRef"}, exclude_none=True)
    payload["clientReferenceId"] = body.clientReferenceId or body.numRef
    datos_qr = {k: v for k, v in {"concept": body.concept, "numRef": body.numRef}.items() if v is not None}
    metadata = {**(body.metadata or {}), **datos_qr}
    if metadata:
        payload["metadata"] = metadata
    else:
        payload.pop("metadata", None)
    payload = {k: v for k, v in payload.items() if v is not None}
    return PaymentLinkRespuesta.model_validate_json(
        _post_pey("/payment-link/create", json.dumps(payload))
    )