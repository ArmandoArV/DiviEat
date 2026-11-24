"""Cuerpo del webhook de Pey cuando entra un pago por QR."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PagoQRRecibido(BaseModel):
    """Campos verbatim de `codi.qr.payment_received`.

    Llegan mas campos de los que usamos (`apiKeyId`, `bankAccountId`,
    `metadata.trackingKey`...). Se admiten y se ignoran: que Pey agregue uno
    nuevo no debe tumbar el endpoint.
    """

    model_config = ConfigDict(extra="allow")

    type: str
    transactionId: str
    codiQrId: str
    amount: Decimal
    numRef: str | None = None
    concept: str | None = None
    datePaid: int | None = None
    metadata: dict | None = None

    @property
    def orden(self) -> str | None:
        """El vinculo firme con nuestra orden viaja en `metadata`."""
        externa = (self.metadata or {}).get("externalMetadata") or {}
        return externa.get("orden")

    @property
    def comensal(self) -> str | None:
        externa = (self.metadata or {}).get("externalMetadata") or {}
        return externa.get("comensal")
