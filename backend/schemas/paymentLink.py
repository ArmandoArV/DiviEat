from pydantic import BaseModel, Field


class PaymentLinkBody(BaseModel):
    amount: float = Field(gt=0)
    successUrl: str = Field(pattern=r"^https://")
    backUrl: str = Field(pattern=r"^https://")
    concept: str | None = Field(default=None, max_length=40)
    numRef: str | None = Field(default=None, pattern=r"^[0-9]{1,7}$")
    hasTip: bool = False
    clientReferenceId: str | None = Field(default=None, max_length=255)
    metadata: dict[str, str | float | bool | None] | None = None
    isMultiplePayments: bool = False


class PaymentLinkRespuesta(BaseModel):
    id: str
    url: str
