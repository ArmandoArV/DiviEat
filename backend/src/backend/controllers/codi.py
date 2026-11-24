"""Casos de uso de cobro CoDi.

Aqui vive la unica traduccion entre centavos (nuestro dominio) y pesos (lo
que Pey recibe), y el freno del modo de prueba. Ninguna de esas dos cosas debe
vivir en una ruta: son reglas, no transporte.
"""

import uuid
from datetime import datetime, timezone

from backend.classes.pey_client import ClientePey
from backend.config import Ajustes
from backend.constants import pey
from backend.models.codi import (
    CobroCreado,
    CobroGuardado,
    CrearCobroPeticion,
    PeyCrearQR,
)
from backend.models.webhook import PagoQRRecibido
from backend.repositories.charges import RepositorioDeCobros
from backend.types.codi import EstadoCobro
from backend.types.errores import ErrorDePey, MontoFueraDePrueba
from backend.utils.money import centavos_a_pesos, referencia_numerica


class ControladorCoDi:
    def __init__(
        self,
        cliente: ClientePey,
        repositorio: RepositorioDeCobros,
        ajustes: Ajustes,
    ) -> None:
        self._cliente = cliente
        self._repositorio = repositorio
        self._ajustes = ajustes

    async def crear_cobro(self, peticion: CrearCobroPeticion) -> CobroCreado:
        pesos = centavos_a_pesos(peticion.centavos)

        # Pey no tiene sandbox: esto se cobra de verdad. Mientras el modo de
        # prueba este encendido, un monto grande es casi seguro un error de
        # unidades (centavos donde iban pesos), no una intencion.
        if self._ajustes.pey_test_mode and pesos > self._ajustes.pey_test_max_amount_mxn:
            raise MontoFueraDePrueba(
                f"Modo de prueba: {pesos} MXN excede el tope de "
                f"{self._ajustes.pey_test_max_amount_mxn} MXN. "
                f"Apaga PEY_TEST_MODE para cobrar de verdad."
            )

        concepto = peticion.concepto or f"DiviEat · Orden {peticion.orden}"

        respuesta = await self._cliente.crear_qr(
            PeyCrearQR(
                amount=pesos,
                concept=concepto[:120],
                expiration=self._ajustes.pey_qr_expiration_seconds,
                numRef=referencia_numerica(peticion.orden, pey.NUM_REF_MAX_DIGITOS),
                generateImage=False,
                bankAccountId=self._ajustes.pey_bank_account_id,
                # `numRef` solo admite digitos, asi que el vinculo firme con
                # nuestra orden viaja aqui: es lo que lee el webhook.
                metadata={"orden": peticion.orden, "comensal": peticion.comensal},
            )
        )

        if not respuesta.qrString:
            raise ErrorDePey("Pey creo el cobro pero no devolvio la cadena del QR")

        cobro = CobroGuardado(
            id=respuesta.id or uuid.uuid4().hex,
            orden=peticion.orden,
            comensal=peticion.comensal,
            centavos=peticion.centavos,
            estado=EstadoCobro.PENDIENTE,
            qr_cadena=respuesta.qrString,
            num_ref=referencia_numerica(peticion.orden, pey.NUM_REF_MAX_DIGITOS),
            creado_en=datetime.now(timezone.utc),
        )
        self._repositorio.guardar(cobro)

        return CobroCreado(
            id=cobro.id,
            orden=cobro.orden,
            comensal=cobro.comensal,
            centavos=cobro.centavos,
            estado=cobro.estado,
            qr_cadena=cobro.qr_cadena,
            qr_imagen_base64=respuesta.qrImage,
            vence_en_segundos=self._ajustes.pey_qr_expiration_seconds,
        )

    def registrar_pago(self, evento: PagoQRRecibido) -> bool:
        """Marca el cobro como pagado. Devuelve si este webhook lo movio.

        False significa "ya estaba pagado", que es lo normal cuando Pey
        reintenta. En ambos casos el endpoint responde 200: un reintento no es
        un error y devolverle un 4xx solo haria que Pey insista.
        """
        if evento.type != pey.EVENTO_PAGO_QR:
            return False
        return self._repositorio.marcar_pagado(evento.codiQrId, evento.transactionId)

    def cobros_de_orden(self, orden: str) -> list[CobroGuardado]:
        return self._repositorio.por_orden(orden)
