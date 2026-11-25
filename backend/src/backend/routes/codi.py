"""Rutas de cobro CoDi. Solo transporte: validan, delegan y responden."""

from fastapi import APIRouter, status

from backend.dependencies import ControladorCoDiDep
from backend.models.codi import CobroCreado, CobroGuardado, CrearCobroPeticion

router = APIRouter(prefix="/codi", tags=["codi"])


@router.post(
    "/cobros",
    response_model=CobroCreado,
    status_code=status.HTTP_201_CREATED,
    summary="Genera un QR CoDi para la parte de un comensal",
)
async def crear_cobro(
    peticion: CrearCobroPeticion, controlador: ControladorCoDiDep
) -> CobroCreado:
    return await controlador.crear_cobro(peticion)


@router.get(
    "/ordenes/{orden}/cobros",
    response_model=list[CobroGuardado],
    summary="Cobros de una orden, con su estado",
)
async def cobros_de_orden(orden: str, controlador: ControladorCoDiDep) -> list[CobroGuardado]:
    return controlador.cobros_de_orden(orden)
