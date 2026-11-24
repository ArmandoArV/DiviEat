"""Errores del dominio, independientes de FastAPI.

El controlador lanza estos; el middleware los traduce a respuestas HTTP. Asi
la logica no necesita saber que existe un servidor web.
"""


class ErrorDeDominio(Exception):
    """Base de todo lo que el backend sabe explicar."""


class PeyNoConfigurado(ErrorDeDominio):
    """Falta `PEY_API_KEY`: no hay con que llamar a Pey."""


class ErrorDePey(ErrorDeDominio):
    """Pey respondio algo que no podemos usar."""

    def __init__(self, mensaje: str, estado: int | None = None, cuerpo: str | None = None):
        super().__init__(mensaje)
        self.estado = estado
        self.cuerpo = cuerpo


class MontoFueraDePrueba(ErrorDeDominio):
    """El modo de prueba esta encendido y el cobro excede el tope."""


class CobroNoEncontrado(ErrorDeDominio):
    pass
