"""Cliente HTTP de Pey.

Es la unica pieza que conoce la forma del cable. Todo lo que sale de aqui ya
esta validado contra nuestros modelos, y todo lo que falla sale como
`ErrorDePey`, no como una excepcion de httpx.
"""

import httpx

from backend.constants import pey
from backend.models.codi import PeyCrearQR, PeyQRCreado
from backend.types.errores import ErrorDePey, PeyNoConfigurado


class ClientePey:
    def __init__(
        self,
        api_key: str,
        base_url: str = pey.BASE_URL,
        tiempo_limite: float = pey.TIEMPO_LIMITE_SEGUNDOS,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._tiempo_limite = tiempo_limite

    @property
    def configurado(self) -> bool:
        return bool(self._api_key)

    async def crear_qr(self, peticion: PeyCrearQR) -> PeyQRCreado:
        """`POST /codi/qr`. Devuelve el QR listo para pintar."""
        if not self.configurado:
            raise PeyNoConfigurado(
                "Falta PEY_API_KEY en el entorno; generala en portal.mipey.mx/developers"
            )

        # `exclude_none` importa: mandar `bankAccountId: null` no es lo mismo
        # que omitirlo, y Pey valida el campo si viene presente.
        cuerpo = peticion.model_dump(exclude_none=True, mode="json")

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._tiempo_limite
            ) as cliente:
                respuesta = await cliente.post(
                    pey.ENDPOINT_CREAR_QR,
                    json=cuerpo,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
        except httpx.RequestError as error:
            raise ErrorDePey(f"No se pudo contactar a Pey: {error}") from error

        if respuesta.status_code != httpx.codes.CREATED:
            raise ErrorDePey(
                f"Pey respondio {respuesta.status_code} al crear el QR",
                estado=respuesta.status_code,
                cuerpo=respuesta.text[:500],
            )

        try:
            return PeyQRCreado.model_validate(respuesta.json())
        except ValueError as error:
            raise ErrorDePey(f"Respuesta de Pey ilegible: {error}") from error
