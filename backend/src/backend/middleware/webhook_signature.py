"""Verificacion de la firma del webhook de Pey.

Pey firma con el estandar Standard Webhooks. Sin esta comprobacion, cualquiera
que conozca la URL podria marcar cuentas como pagadas: es la diferencia entre
un webhook y un formulario abierto.
"""

from fastapi import Request

from backend.config import Ajustes
from standardwebhooks import Webhook, WebhookVerificationError


class FirmaInvalida(Exception):
    pass


class VerificadorDeWebhook:
    def __init__(self, secreto: str) -> None:
        self._secreto = secreto

    @property
    def configurado(self) -> bool:
        return bool(self._secreto)

    async def cuerpo_verificado(self, peticion: Request) -> bytes:
        """Devuelve el cuerpo crudo si la firma cuadra.

        Tiene que ser el cuerpo **tal como llego**: volver a serializar el
        JSON cambia espacios y orden de llaves, y la firma deja de cuadrar.
        """
        crudo = await peticion.body()

        if not self.configurado:
            raise FirmaInvalida(
                "Falta PEY_WEBHOOK_SECRET: no se puede verificar la firma del webhook"
            )

        try:
            Webhook(self._secreto).verify(crudo, dict(peticion.headers))
        except WebhookVerificationError as error:
            raise FirmaInvalida(f"Firma del webhook invalida: {error}") from error

        return crudo


def construir_verificador(ajustes: Ajustes) -> VerificadorDeWebhook:
    return VerificadorDeWebhook(ajustes.pey_webhook_secret)
