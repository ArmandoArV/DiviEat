"""Valores fijos del contrato de Pey.

Salen de la especificacion OpenAPI publica (https://docs.pey.mx/openapi.json).
Viven aqui y no repartidos por el codigo para que, cuando Pey cambie un limite,
haya un solo lugar que tocar.
"""

BASE_URL = "https://api.pey.mx"

ENDPOINT_CREAR_QR = "/codi/qr"
ENDPOINT_TRANSACCIONES_QR = "/transaction/codi/qr/{id}"

# `expiration` en segundos: 0 significa sin vencimiento, pero si se define,
# Pey rechaza cualquier valor por debajo de 360 (seis minutos).
EXPIRACION_SIN_VENCIMIENTO = 0
EXPIRACION_MINIMA_SEGUNDOS = 360

# `numRef` es la referencia numerica del CoDi: solo digitos, hasta siete.
NUM_REF_MAX_DIGITOS = 7

# Limites de `metadata` declarados por Pey.
METADATA_MAX_PARES = 50
METADATA_MAX_LARGO_LLAVE = 40
METADATA_MAX_LARGO_VALOR = 500

# Tipo de evento del webhook cuando entra un pago por QR.
EVENTO_PAGO_QR = "codi.qr.payment_received"

TIEMPO_LIMITE_SEGUNDOS = 20.0
