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

## Docker

```bash
docker build -t divieat-codi .
docker run --rm -p 8080:8080 --env-file .env divieat-codi
```

Multi-stage onto `scratch`: 17.6 MB, no shell, no package manager, running as
uid 65534. The CA bundle is copied in because both outbound calls verify TLS —
Pey over HTTPS and Mongo Atlas over `mongodb+srv` — and without it every one
fails at handshake.

`.env` is in `.dockerignore`. A secret baked into a layer survives in the
image history even if a later layer deletes the file, so it must never get in
to begin with; pass it at run time with `--env-file`.

There is no `HEALTHCHECK` instruction: `scratch` has no shell to run one.
Probe `GET /health` over HTTP from the orchestrator, which is where a liveness
check belongs anyway.

## Testing it

### Locally

```bash
docker compose up --build        # API + a throwaway Mongo on :8080
curl localhost:8080/health
```

Without `PEY_API_KEY` the API still boots and `/health` says so, which
exercises everything except an actual charge.

To prove the webhook path without Pey, insert a pending charge and post a
signed body at it. This is the whole chain — signature, Mongo write,
idempotency — and it needs no key:

```bash
export PEY_WEBHOOK_SECRET='whsec_cHJ1ZWJhLWRlLWhhY2thdGhvbg=='
docker compose up -d
docker compose exec -T mongo mongosh --quiet divieat --eval '
  db.codi_charges.insertOne({id:"qr-demo",order:"2471",diner:"mariana",
    cents:NumberLong("100"),status:"pending",qrString:"X",numRef:"2471",
    createdAt:new Date()})'
```

Then sign `{"type":"codi.qr.payment_received","codiQrId":"qr-demo",...}` with
that secret into `webhook-id`, `webhook-timestamp` and `webhook-signature`.
Delivering it twice should answer `applied:true` then `applied:false`, and
leave the charge paid exactly once.

### Against Pey for real

**Pey has to reach the webhook, so it needs a public HTTPS URL.** `localhost`
is not reachable from Pey's side, which is the real reason this gets deployed
rather than demoed from a laptop. Either deploy (below) or open a tunnel
(`cloudflared tunnel --url http://localhost:8080`) and register whatever URL
you get in the portal, under the gear next to the API key.

Pey has no sandbox: charges are real. Leave `PEY_TEST_MODE=true` and test with
$0.01 until the demo is ready to move actual money.

## Deploying to Azure

Container Apps, described in Bicep under `infra/`.

```bash
export SUBSCRIPTION='<id or name>'
export PEY_API_KEY='...' PEY_WEBHOOK_SECRET='...' MONGODB_URI='...'
./infra/deploy.sh
```

Two passes on purpose: the registry has to exist before there is anywhere to
push, and the image has to exist before the app can run it. The script builds
inside ACR, so no Docker daemon is needed and the image comes out linux/amd64
whatever the laptop is. It prints the webhook URL to register in the portal.

### What it costs

Sized so that idling is close to free:

| | |
|---|---|
| Container App | `minReplicas: 0` — **no charge while idle**, 0.25 vCPU / 0.5 Gi when awake |
| Container Apps environment | no charge on the consumption plan |
| Log Analytics | capped at 1 GB/day, 30-day retention |
| Container Registry | Basic, **the only thing that bills continuously** (a few dollars a month) |
| Database | off by default — a free Atlas M0 cluster costs nothing |

`deployDatabase=true` swaps in Cosmos DB serverless instead, which bills per
request rather than per hour.

**Raise `minReplicas` to 1 before a live demo.** Scaling to zero is what makes
idling free, and the price is a cold start on the first request after a quiet
spell — which, in front of judges, reads as the app being broken.

## Endpoints

| | |
|---|---|
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
