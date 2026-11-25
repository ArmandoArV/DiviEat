package utils

import (
	"strconv"
	"testing"
	"time"
)

const testSecret = "whsec_c2VjcmV0LWZvci10ZXN0cw==" // not a real key

func newVerifier(t *testing.T) *WebhookVerifier {
	t.Helper()
	v, err := NewWebhookVerifier(testSecret, 5*time.Minute)
	if err != nil {
		t.Fatalf("NewWebhookVerifier: %v", err)
	}
	return v
}

func TestAcceptsItsOwnSignature(t *testing.T) {
	v := newVerifier(t)
	body := []byte(`{"type":"codi.qr.payment_received","amount":1}`)
	now := time.Now()

	if err := v.Verify(body, "msg_1", unix(now), v.Sign(body, "msg_1", now)); err != nil {
		t.Fatalf("a signature we just produced should verify: %v", err)
	}
}

func TestRejectsATamperedBody(t *testing.T) {
	v := newVerifier(t)
	now := time.Now()
	signature := v.Sign([]byte(`{"amount":1}`), "msg_1", now)

	// This is the attack the check exists for: same headers, bigger amount.
	if err := v.Verify([]byte(`{"amount":99999}`), "msg_1", unix(now), signature); err == nil {
		t.Fatal("a body that was not signed must not verify")
	}
}

func TestRejectsAReplayedTimestamp(t *testing.T) {
	v := newVerifier(t)
	body := []byte(`{"amount":1}`)
	old := time.Now().Add(-30 * time.Minute)

	if err := v.Verify(body, "msg_1", unix(old), v.Sign(body, "msg_1", old)); err == nil {
		t.Fatal("a correctly signed but stale call must be refused")
	}
}

func TestRejectsMissingHeaders(t *testing.T) {
	v := newVerifier(t)
	body := []byte(`{"amount":1}`)
	now := time.Now()

	if err := v.Verify(body, "", unix(now), v.Sign(body, "msg_1", now)); err == nil {
		t.Fatal("a missing webhook-id must be refused, not ignored")
	}
	if err := v.Verify(body, "msg_1", unix(now), ""); err == nil {
		t.Fatal("a missing signature must be refused")
	}
}

func TestAcceptsWhenOneOfSeveralSignaturesMatches(t *testing.T) {
	v := newVerifier(t)
	body := []byte(`{"amount":1}`)
	now := time.Now()
	// During a secret rotation Pey sends both; one matching is enough.
	header := "v1,AAAA " + v.Sign(body, "msg_1", now)

	if err := v.Verify(body, "msg_1", unix(now), header); err != nil {
		t.Fatalf("one valid signature among several should pass: %v", err)
	}
}

func unix(t time.Time) string { return strconv.FormatInt(t.Unix(), 10) }
