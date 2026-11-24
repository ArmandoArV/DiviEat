"""Configuracion leida del entorno.

Nada de llaves en el codigo: todo entra por `.env`, que esta en `.gitignore`.
"""

from decimal import Decimal
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.constants import pey


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "divieat"

    pey_api_key: str = ""
    pey_base_url: str = pey.BASE_URL
    pey_webhook_secret: str = ""
    pey_bank_account_id: str | None = None
    pey_qr_expiration_seconds: int = 900

    # Pey no tiene sandbox: se prueba en produccion con dinero real. Mientras
    # `pey_test_mode` este encendido, el backend se niega a cobrar por encima
    # del tope, para que un cero de mas no se convierta en un cargo de verdad.
    pey_test_mode: bool = True
    pey_test_max_amount_mxn: Decimal = Field(default=Decimal("1"))

    @field_validator("pey_qr_expiration_seconds")
    @classmethod
    def _expiracion_valida(cls, valor: int) -> int:
        if valor == pey.EXPIRACION_SIN_VENCIMIENTO:
            return valor
        if valor < pey.EXPIRACION_MINIMA_SEGUNDOS:
            raise ValueError(
                f"Pey rechaza vigencias menores a {pey.EXPIRACION_MINIMA_SEGUNDOS}s; "
                f"usa 0 para que el QR no venza"
            )
        return valor

    @property
    def pey_configurado(self) -> bool:
        return bool(self.pey_api_key)


@lru_cache
def obtener_ajustes() -> Ajustes:
    return Ajustes()
