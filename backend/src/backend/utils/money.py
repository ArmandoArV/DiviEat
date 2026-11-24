"""Conversion entre la moneda del dominio y la que espera Pey.

DiviEat guarda dinero en **centavos enteros** —misma regla que el modulo `ai/`
y que el frontend— porque la cuenta de una mesa cuadra o no cuadra, y un float
pierde esa discusion. Pey, en cambio, recibe el monto en **pesos**.

La conversion es el unico punto donde se cruzan esas dos unidades. Va con
Decimal: `12050 / 100` en float da 120.5 por suerte, pero no siempre.
"""

from decimal import Decimal, ROUND_HALF_UP

CENTAVOS_POR_PESO = Decimal(100)


def centavos_a_pesos(centavos: int) -> Decimal:
    """Pasa centavos enteros a pesos con dos decimales exactos."""
    if centavos < 0:
        raise ValueError("Un cobro no puede ser negativo")
    return (Decimal(centavos) / CENTAVOS_POR_PESO).quantize(Decimal("0.01"))


def pesos_a_centavos(pesos: Decimal | float | int | str) -> int:
    """Pasa pesos a centavos enteros, redondeando al centavo mas cercano.

    El webhook de Pey entrega el monto en pesos como numero JSON, asi que al
    volver al dominio hay que cerrar el circulo.
    """
    valor = Decimal(str(pesos))
    return int((valor * CENTAVOS_POR_PESO).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def referencia_numerica(texto: str, max_digitos: int) -> str:
    """Construye un `numRef` valido a partir de un identificador cualquiera.

    Pey solo acepta digitos, hasta siete. Un numero de orden como "2471" pasa
    tal cual; uno alfanumerico como "7A2K" pierde las letras, asi que lo que
    queda sirve de pista para conciliar, no de identificador: el vinculo firme
    es `metadata`.
    """
    digitos = "".join(c for c in texto if c.isdigit())
    return digitos[-max_digitos:] if digitos else "0"
