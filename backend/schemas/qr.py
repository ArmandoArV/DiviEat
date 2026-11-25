from pydantic import BaseModel, Field


class QrBody(BaseModel):
    amount: float = Field(ge=0)
    concept: str = Field(max_length=40)
    expiration: int = Field(ge=0)
    numRef: str = Field(pattern=r"^[0-9]{1,7}$")
    generateImage: bool = False
    bankAccountId: str | None = None
    metadata: dict = {}


class QrRespuesta(BaseModel):
    id: str
    qrString: str
    qrImage: str | None = None
