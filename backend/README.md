# DiviEat · backend

FastAPI + MongoDB. Cobros **CoDi a través de [Pey](https://docs.pey.mx)**.

## Estructura

```
app.py                  arranque: CORS, routers, ciclo de vida
database.py             conexion a Mongo
src/backend/
  config.py             ajustes leidos del .env
  constants/pey.py      limites del contrato de Pey, en un solo lugar
  types/                enums del dominio y errores
  models/               esquemas: los nuestros (centavos) y los del cable (pesos)
  utils/money.py        la unica conversion centavos <-> pesos
  classes/pey_client.py cliente HTTP de Pey
  repositories/         acceso a Mongo
  controllers/          casos de uso
  middleware/           firma del webhook y traduccion de errores a HTTP
  routes/               transporte
tests/                  no necesitan Mongo ni red
```

## Configurar

```bash
cp .env.example .env     # y llena PEY_API_KEY y PEY_WEBHOOK_SECRET
uv sync
uv run fastapi dev app.py
uv run pytest
```

La llave se genera en [portal.mipey.mx/developers](https://portal.mipey.mx/developers).
El **`.env` está en `.gitignore`**: esa llave mueve dinero real.

## Cosas que cuesta descubrir tarde

- **Pey cobra en PESOS; el dominio guarda CENTAVOS.** `utils/money.py` es el
  único punto donde se cruzan. Mandar centavos donde van pesos cobra 100x.
- **Pey no tiene sandbox.** Se prueba en producción con montos de $0.01 MXN.
  Por eso existe `PEY_TEST_MODE`: mientras esté encendido, el backend rechaza
  cobros por encima de `PEY_TEST_MAX_AMOUNT_MXN` antes de llamar a Pey.
- **`numRef` solo acepta hasta 7 dígitos.** Un número de orden alfanumérico no
  cabe, así que el vínculo firme con la orden viaja en `metadata`, que es lo
  que lee el webhook. `numRef` queda como pista para conciliar.
- **La firma del webhook se verifica sobre los bytes crudos.** Volver a
  serializar el JSON cambia espacios y orden de llaves, y la firma deja de
  cuadrar. Sin esa verificación, cualquiera que sepa la URL podría marcar
  cuentas como pagadas.
- **El webhook siempre responde 200, incluso en un reintento.** `marcar_pagado`
  es idempotente: el segundo golpe no mueve nada. Devolver 4xx solo lograría
  que Pey insista.
- **Si Mongo no responde, el webhook debe fallar fuerte**, para que Pey
  reintente. Tragarse ese error perdería el pago en silencio.

## Endpoints

| | |
|---|---|
| `POST /codi/cobros` | genera el QR CoDi de la parte de un comensal |
| `GET /codi/ordenes/{orden}/cobros` | cobros de una orden y su estado |
| `POST /webhooks/pey/codi` | pago recibido (firmado por Pey) |
| `GET /salud` | si la llave está configurada y si el modo prueba está activo |

La URL del webhook se registra en el portal, en el engrane junto a la API key.
