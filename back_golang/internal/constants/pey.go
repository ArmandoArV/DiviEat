// Package constants pins the fixed values of external contracts, so that a
// limit changing upstream means touching exactly one file.
package constants

import "time"

// Taken from Pey's public OpenAPI spec: https://docs.pey.mx/openapi.json
const (
	PeyBaseURL      = "https://api.pey.mx"
	PeyCreateQRPath = "/codi/qr"

	// `expiration` in seconds. 0 means no expiry, but once set, Pey rejects
	// anything below 360 (six minutes).
	PeyNoExpiry        = 0
	PeyMinExpirySecond = 360

	// `numRef` is CoDi's numeric reference: digits only, seven at most.
	PeyNumRefMaxDigits = 7

	// Limits Pey declares for `metadata`.
	PeyMetadataMaxPairs       = 50
	PeyMetadataMaxKeyLength   = 40
	PeyMetadataMaxValueLength = 500

	// Webhook event fired when a QR payment lands.
	PeyQRPaymentEvent = "codi.qr.payment_received"

	PeyRequestTimeout = 20 * time.Second
)

// Standard Webhooks headers, used to verify Pey's signature.
const (
	HeaderWebhookID        = "webhook-id"
	HeaderWebhookTimestamp = "webhook-timestamp"
	HeaderWebhookSignature = "webhook-signature"

	WebhookSecretPrefix = "whsec_"
	// How far a webhook timestamp may drift before it is treated as a replay.
	WebhookTolerance = 5 * time.Minute
)

// Mongo collections.
const ChargesCollection = "codi_charges"
