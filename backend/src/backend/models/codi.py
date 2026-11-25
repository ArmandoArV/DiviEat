"""Esquemas del cobro CoDi: los nuestros y los del cable con Pey.

Estan separados a proposito. Los de Pey hablan en pesos y con sus nombres en
ingles; los nuestros hablan en centavos. Si se mezclan, tarde o temprano
alguien manda centavos donde iban pesos y cobra cien veces de mas.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.constants import pey
from backend.types.codi import EstadoCobro


class CrearCobroPeticion(BaseModel):
    """Lo que pide el frontend: siempre en centavos."""

    orden: str = Field(min_length=1, max_length=32)
    comensal: str = Field(min_length=1, max_length=64)
    centavos: int = Field(gt=0, description="Importe a cobrar, en centavos enteros")
    concepto: str | None = Field(default=None, max_length=120)


class CobroCreado(BaseModel):
    """Lo que devolvemos al frontend para que pinte el QR."""

    id: str
    orden: str
    comensal: str
    centavos: int
    estado: EstadoCobro
    qr_cadena: str
    qr_imagen_base64: str | None = None
    vence_en_segundos: int


# --- Cable con Pey -------------------------------------------------------
# Nombres verbatim del contrato de Pey; no los traduzcas.


class PeyCrearQR(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal = Field(ge=0, description="Monto en PESOS, no en centavos")
    concept: str | None = None
    expiration: int = pey.EXPIRACION_SIN_VENCIMIENTO
    numRef: str = "0"
    generateImage: bool = False
    bankAccountId: str | None = None
    metadata: dict[str, str] | None = None


class PeyQRCreado(BaseModel):
    """Respuesta 201 de `POST /codi/qr`.

    Pey no marca ningun campo como obligatorio, asi que todos entran
    opcionales y la validacion de que al menos venga `qrString` la hace el
    controlador: sin esa cadena no hay nada que mostrar.
    """

    id: str | None = None
    qrString: str | None = None
    qrImage: str | None = None


class CobroGuardado(BaseModel):
    """Lo que vive en Mongo."""

    id: str
    orden: str
    comensal: str
    centavos: int
    estado: EstadoCobro = EstadoCobro.PENDIENTE
    qr_cadena: str
    num_ref: str
    creado_en: datetime
    pagado_en: datetime | None = None
    transaccion_id: str | None = None
