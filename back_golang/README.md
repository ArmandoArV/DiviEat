# DiviEat · CoDi API (Go)

[Fiber v3](https://gofiber.io) + MongoDB. Creates **CoDi QR charges through
[Pey](https://docs.pey.mx)** and confirms them from Pey's webhook.

This is one of two backends. It owns CoDi charges; the Python service keeps
the ticket OCR, which needs the PyTorch stack.

## Layout

```
main.go                      boot: config, Mongo, routes
internal/
  config/        settings read from the environment
  constants/     Pey's contract limits, pinned in one place
  types/         domain enums and errors, no transport knowledge
  models/        wire and storage shapes — ours in cents, Pey's in pesos
  utils/         money (integer cents) and webhook signature verification
  classes/       the Pey HTTP client
  repositories/  the only thing that touches Mongo
  controllers/   use cases
  middleware/    signature guard and error-to-HTTP translation
  routes/        transport only
```

`classes/` mirrors the Python backend's folder names so moving between the two
is not a puzzle. A Go-only codebase would call it `clients`.

## Run

```bash
cp .env.example .env     # fill PEY_API_KEY and PEY_WEBHOOK_SECRET
go run .                 # :8080
go test ./...
```

The key comes from [portal.mipey.mx/developers](https://portal.mipey.mx/developers).
**`.env` is gitignored**: that key moves real money.

## Endpoints

| | |
|---|---|
| `POST /auth/register` | registers a user (`name`, `email`, `role`, `password`) and returns a JWT |
| `POST /auth/login` | authenticates a user and returns a JWT |
| `GET /auth/me` | returns the authenticated user (`Authorization: Bearer <token>`) |
| `POST /codi/charges` | creates the CoDi QR for one diner's share |
| `GET /codi/orders/:order/charges` | charges on an order and their status |
| `POST /webhooks/pey/codi` | payment received, signed by Pey |
| `GET /health` | whether the key is set and test mode is on |

Register the webhook URL in the portal, under the gear next to the API key.

## Things that are expensive to learn late

- **Pey charges in PESOS; the domain stores CENTS.** `utils.Cents` is an
  integer and `Pesos` is the only type that crosses over, serialising through
  a string so a float never touches the money. `TestTheAmountReachesPeyInPesosNotCents`
  is there to keep it that way.
- **Pey has no sandbox.** You test in production with $0.01 charges, so
  `PEY_TEST_MODE` refuses anything above the ceiling *before* the request
  leaves. A big amount while testing is almost always cents passed where
  pesos go — a 100x error, not an intention.
- **`numRef` takes seven digits at most.** An alphanumeric order number does
  not survive it, so the firm link to the order rides in `metadata`, which is
  what the webhook reads back. `numRef` stays a reconciliation hint.
- **The signature is verified over the raw bytes**, before the body is parsed.
  Re-serialising the JSON reorders keys and the signature stops matching.
  Without the check, anyone who learns the URL could mark bills as paid.
- **The webhook always answers 200, retries included.** Marking a charge paid
  is idempotent; a second delivery moves nothing. Answering 4xx would only
  make Pey insist.
- **Booting tolerates a dead Mongo** so `/health` can say what is missing,
  but the webhook does not: if the write fails it must fail loudly, or the
  payment is swallowed and Pey never retries.
