"""Acceso a Mongo para los cobros CoDi.

Nada mas toca la coleccion directamente: si manana el almacenamiento cambia,
cambia aqui y el controlador ni se entera.
"""

from datetime import datetime, timezone

import logging

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from backend.models.codi import CobroGuardado
from backend.types.codi import EstadoCobro

log = logging.getLogger(__name__)

COLECCION = "cobros_codi"


class RepositorioDeCobros:
    def __init__(self, db: Database) -> None:
        self._cobros: Collection = db[COLECCION]

    def asegurar_indices(self) -> bool:
        """Crea los indices si Mongo responde.

        No revienta si no hay base: la API debe poder arrancar para que
        `/salud` conteste y se vea que lo que falta es Mongo, no el servidor.
        """
        try:
            # Por `id` se busca al confirmar el pago; por orden se arma la cuenta.
            self._cobros.create_index("id", unique=True)
            self._cobros.create_index([("orden", 1), ("estado", 1)])
            self._cobros.create_index("transaccion_id", sparse=True)
            return True
        except PyMongoError as error:
            log.warning("No se pudieron crear los indices de %s: %s", COLECCION, error)
            return False

    def guardar(self, cobro: CobroGuardado) -> None:
        self._cobros.update_one(
            {"id": cobro.id},
            {"$set": cobro.model_dump(mode="json")},
            upsert=True,
        )

    def obtener(self, id_cobro: str) -> CobroGuardado | None:
        documento = self._cobros.find_one({"id": id_cobro}, {"_id": 0})
        return CobroGuardado.model_validate(documento) if documento else None

    def por_orden(self, orden: str) -> list[CobroGuardado]:
        return [
            CobroGuardado.model_validate(d)
            for d in self._cobros.find({"orden": orden}, {"_id": 0})
        ]

    def marcar_pagado(self, id_cobro: str, transaccion_id: str) -> bool:
        """Idempotente a proposito: Pey reintenta el webhook.

        El filtro exige que el cobro siga pendiente, asi que el segundo intento
        no vuelve a mover nada y devuelve False — que es como el controlador
        distingue "lo acabo de cobrar" de "ya estaba cobrado".
        """
        resultado = self._cobros.update_one(
            {"id": id_cobro, "estado": EstadoCobro.PENDIENTE.value},
            {
                "$set": {
                    "estado": EstadoCobro.PAGADO.value,
                    "transaccion_id": transaccion_id,
                    "pagado_en": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        return resultado.modified_count == 1
