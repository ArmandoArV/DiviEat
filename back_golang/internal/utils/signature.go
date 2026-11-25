package utils

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"strconv"
	"strings"
	"time"
)

// WebhookVerifier checks Standard Webhooks signatures (standardwebhooks.com),
// which is what Pey uses to sign its calls.
//
// Without this check, anyone who learns the webhook URL could mark bills as
// paid. It is implemented here rather than pulled in because the algorithm is
// forty lines of well-specified HMAC, and forty lines we can audit beat a
// dependency we cannot resolve.
type WebhookVerifier struct {
	key       []byte
	tolerance time.Duration
}

func NewWebhookVerifier(secret string, tolerance time.Duration) (*WebhookVerifier, error) {
	if secret == "" {
		return nil, fmt.Errorf("empty webhook secret")
	}
	raw := strings.TrimPrefix(secret, "whsec_")
	key, err := base64.StdEncoding.DecodeString(raw)
	if err != nil {
		return nil, fmt.Errorf("webhook secret is not base64: %w", err)
	}
	return &WebhookVerifier{key: key, tolerance: tolerance}, nil
}

// Verify takes the body exactly as received. Re-serializing the JSON first
// would reorder keys and change whitespace, and the signature would stop
// matching for reasons that look like an attack.
func (v *WebhookVerifier) Verify(payload []byte, msgID, timestamp, signatures string) error {
	if msgID == "" || timestamp == "" || signatures == "" {
		return fmt.Errorf("missing webhook-id, webhook-timestamp or webhook-signature")
	}

	seconds, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil {
		return fmt.Errorf("webhook-timestamp is not a unix time: %q", timestamp)
	}
	drift := time.Since(time.Unix(seconds, 0))
	if drift < -v.tolerance || drift > v.tolerance {
		return fmt.Errorf("webhook timestamp is %s off; treating it as a replay", drift.Round(time.Second))
	}

	mac := hmac.New(sha256.New, v.key)
	mac.Write([]byte(msgID + "." + timestamp + "."))
	mac.Write(payload)
	expected := mac.Sum(nil)

	// The header may carry several space-separated versioned signatures, so
	// that a secret can be rotated without dropping calls mid-flight.
	for _, candidate := range strings.Split(signatures, " ") {
		version, encoded, found := strings.Cut(candidate, ",")
		if !found || version != "v1" {
			continue
		}
		given, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil {
			continue
		}
		// Constant time: a byte-by-byte compare leaks how much of a forged
		// signature was right.
		if hmac.Equal(given, expected) {
			return nil
		}
	}
	return fmt.Errorf("no signature in the header matched")
}

// Sign produces the header value for a payload. Used by the tests, and by
// anything that needs to stand in for Pey.
func (v *WebhookVerifier) Sign(payload []byte, msgID string, at time.Time) string {
	mac := hmac.New(sha256.New, v.key)
	mac.Write([]byte(msgID + "." + strconv.FormatInt(at.Unix(), 10) + "."))
	mac.Write(payload)
	return "v1," + base64.StdEncoding.EncodeToString(mac.Sum(nil))
}
