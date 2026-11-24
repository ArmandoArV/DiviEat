"""Traduce los errores del dominio a respuestas HTTP.

El controlador no sabe de codigos de estado; este modulo es el unico lugar
donde se decide que significa cada falla para el cliente.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.middleware.webhook_signature import FirmaInvalida
from backend.types.errores import (
    CobroNoEncontrado,
    ErrorDePey,
    MontoFueraDePrueba,
    PeyNoConfigurado,
)

log = logging.getLogger(__name__)

CODIGOS = {
    PeyNoConfigurado: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorDePey: status.HTTP_502_BAD_GATEWAY,
    MontoFueraDePrueba: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CobroNoEncontrado: status.HTTP_404_NOT_FOUND,
    FirmaInvalida: status.HTTP_401_UNAUTHORIZED,
}


def registrar_manejadores(app: FastAPI) -> None:
    for excepcion, codigo in CODIGOS.items():
        app.add_exception_handler(excepcion, _manejar(codigo))


def _manejar(codigo: int):
    async def manejador(_: Request, error: Exception) -> JSONResponse:
        detalle = str(error)
        if isinstance(error, ErrorDePey):
            # El cuerpo de Pey va al log, no a la respuesta: puede traer datos
            # de la cuenta que recibe el dinero.
            log.error("Pey fallo (%s): %s", error.estado, error.cuerpo)
            detalle = str(error)
        return JSONResponse(status_code=codigo, content={"error": detalle})

    return manejador
