import http.client
import json
import os

from dotenv import load_dotenv

from schemas.qr import QrBody, QrRespuesta

load_dotenv()




def generar_qr_codi(body: QrBody) -> QrRespuesta:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {os.getenv('PEY_API_TOKEN')}",
    }

    conn = http.client.HTTPSConnection(os.getenv("PEY_HOST"), timeout=10)
    try:
        conn.request("POST", "/codi/qr", body.model_dump_json(exclude_none=True), headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
    finally:
        conn.close()

    if res.status >= 400:
        raise Exception(f"Pey respondio {res.status}: {data}")
    return QrRespuesta.model_validate_json(data)