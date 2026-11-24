"""Tipos compartidos del dominio de cobros CoDi."""

from enum import StrEnum


class EstadoCobro(StrEnum):
    """Ciclo de vida de un cobro CoDi desde que se genera el QR."""

    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    VENCIDO = "vencido"


class TipoEventoWebhook(StrEnum):
    PAGO_QR_RECIBIDO = "codi.qr.payment_received"
