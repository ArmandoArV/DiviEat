# syntax=docker/dockerfile:1

# --- build ---------------------------------------------------------------
FROM golang:1.27-alpine AS build

WORKDIR /src

# Dependencies first: this layer only changes when go.mod/go.sum do, so
# editing source does not re-download the module graph.
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download

COPY . .

# CGO off gives a static binary, which is what lets the final stage be
# `scratch`. -trimpath keeps build paths out of the binary; -s -w drop the
# symbol table and DWARF, which this does not need in production.
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build \
      -trimpath -ldflags="-s -w" -o /out/api .

# --- run -----------------------------------------------------------------
FROM scratch

# Both outbound calls need to verify TLS: Pey over HTTPS and Mongo Atlas over
# mongodb+srv. Without the CA bundle every one of them fails at handshake.
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

COPY --from=build /out/api /api

# nobody. The process never writes to disk and never needs root.
USER 65534:65534

ENV PORT=8080
EXPOSE 8080

# No shell in `scratch`, so there is no HEALTHCHECK here on purpose: probe
# GET /health over HTTP from the orchestrator, which is where it belongs.
ENTRYPOINT ["/api"]
