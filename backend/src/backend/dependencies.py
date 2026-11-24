"""Cableado de dependencias para FastAPI.

Un solo lugar arma el cliente, el repositorio y el controlador. Las rutas
piden el controlador y no saben como se construye.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from backend.classes.pey_client import ClientePey
from backend.config import Ajustes, obtener_ajustes
from backend.controllers.codi import ControladorCoDi
from backend.middleware.webhook_signature import VerificadorDeWebhook
from backend.repositories.charges import RepositorioDeCobros
from database import db

AjustesDep = Annotated[Ajustes, Depends(obtener_ajustes)]


@lru_cache
def obtener_controlador_codi() -> ControladorCoDi:
    ajustes = obtener_ajustes()
    return ControladorCoDi(
        cliente=ClientePey(
            api_key=ajustes.pey_api_key,
            base_url=ajustes.pey_base_url,
        ),
        repositorio=RepositorioDeCobros(db),
        ajustes=ajustes,
    )


@lru_cache
def obtener_verificador() -> VerificadorDeWebhook:
    return VerificadorDeWebhook(obtener_ajustes().pey_webhook_secret)


ControladorCoDiDep = Annotated[ControladorCoDi, Depends(obtener_controlador_codi)]
VerificadorDep = Annotated[VerificadorDeWebhook, Depends(obtener_verificador)]
