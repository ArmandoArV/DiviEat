package controllers

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/classes"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/config"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

// memoryStore stands in for Mongo so the tests need no server.
type memoryStore struct {
	charges map[string]models.Charge
}

func newStore(seed ...models.Charge) *memoryStore {
	s := &memoryStore{charges: map[string]models.Charge{}}
	for _, c := range seed {
		s.charges[c.ID] = c
	}
	return s
}

func (s *memoryStore) Save(_ context.Context, charge models.Charge) error {
	s.charges[charge.ID] = charge
	return nil
}

func (s *memoryStore) ByOrder(_ context.Context, order string) ([]models.Charge, error) {
	var out []models.Charge
	for _, c := range s.charges {
		if c.Order == order {
			out = append(out, c)
		}
	}
	return out, nil
}

func (s *memoryStore) MarkPaid(_ context.Context, id, transactionID string) (bool, error) {
	charge, ok := s.charges[id]
	if !ok || charge.Status != types.ChargePending {
		return false, nil
	}
	charge.Status = types.ChargePaid
	charge.TransactionID = transactionID
	s.charges[id] = charge
	return true, nil
}

// fakePey records what Pey would have received and answers a created QR.
func fakePey(t *testing.T, seen *map[string]any) *httptest.Server {
	t.Helper()
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		var parsed map[string]any
		if err := json.Unmarshal(body, &parsed); err != nil {
			t.Errorf("we sent Pey something that is not JSON: %v", err)
		}
		*seen = parsed
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{"id":"qr-1","qrString":"CODI-PAYLOAD"}`))
	}))
}

func settings(server string, testMode bool) *config.Config {
	return &config.Config{
		PeyAPIKey:     "test-key",
		PeyBaseURL:    server,
		PeyQRExpiry:   900,
		TestMode:      testMode,
		TestMaxAmount: 100, // $1.00
	}
}

func TestTheAmountReachesPeyInPesosNotCents(t *testing.T) {
	// This is the whole point of keeping two separate models. $276.00 must
	// go out as 276.00; sending 27600 would charge a hundred times too much.
	var seen map[string]any
	server := fakePey(t, &seen)
	defer server.Close()

	cfg := settings(server.URL, false)
	ctrl := NewCodiController(classes.NewPeyClient("k", server.URL), newStore(), cfg)

	if _, err := ctrl.CreateCharge(context.Background(), models.CreateChargeRequest{
		Order: "2471", Diner: "mariana", Cents: 27600,
	}); err != nil {
		t.Fatalf("CreateCharge: %v", err)
	}

	if got := seen["amount"]; got != 276.0 {
		t.Errorf("Pey received amount=%v, expected 276 pesos", got)
	}
	if got := seen["numRef"]; got != "2471" {
		t.Errorf("numRef = %v, expected the order number", got)
	}
	meta, _ := seen["metadata"].(map[string]any)
	if meta["order"] != "2471" || meta["diner"] != "mariana" {
		t.Errorf("metadata = %v; the firm link to the order has to ride here", meta)
	}
}

func TestTestModeRefusesBeforeCallingPey(t *testing.T) {
	var seen map[string]any
	server := fakePey(t, &seen)
	defer server.Close()

	cfg := settings(server.URL, true) // ceiling $1.00
	ctrl := NewCodiController(classes.NewPeyClient("k", server.URL), newStore(), cfg)

	_, err := ctrl.CreateCharge(context.Background(), models.CreateChargeRequest{
		Order: "2471", Diner: "mariana", Cents: 27600,
	})

	var testErr *types.TestModeError
	if !errors.As(err, &testErr) {
		t.Fatalf("expected the spending guard to fire, got %v", err)
	}
	if seen != nil {
		t.Error("the guard must stop the call before Pey ever sees it")
	}
}

func TestUnderTheCeilingTestModeLetsItThrough(t *testing.T) {
	var seen map[string]any
	server := fakePey(t, &seen)
	defer server.Close()

	cfg := settings(server.URL, true)
	ctrl := NewCodiController(classes.NewPeyClient("k", server.URL), newStore(), cfg)

	charge, err := ctrl.CreateCharge(context.Background(), models.CreateChargeRequest{
		Order: "2471", Diner: "mariana", Cents: 1,
	})
	if err != nil {
		t.Fatalf("a one-cent charge should pass the guard: %v", err)
	}
	if charge.QRString != "CODI-PAYLOAD" {
		t.Errorf("QRString = %q", charge.QRString)
	}
}

func TestWithoutAKeyTheFailureIsClear(t *testing.T) {
	cfg := settings("", false)
	ctrl := NewCodiController(classes.NewPeyClient("", ""), newStore(), cfg)

	_, err := ctrl.CreateCharge(context.Background(), models.CreateChargeRequest{
		Order: "2471", Diner: "mariana", Cents: 1,
	})
	if !errors.Is(err, types.ErrPeyNotConfigured) {
		t.Fatalf("expected ErrPeyNotConfigured, got %v", err)
	}
}

func TestARetryDoesNotChargeTwice(t *testing.T) {
	store := newStore(models.Charge{
		ID: "qr-1", Order: "2471", Diner: "mariana", Cents: 100,
		Status: types.ChargePending,
	})
	ctrl := NewCodiController(classes.NewPeyClient("k", ""), store, settings("", false))

	event := models.QRPaymentReceived{
		Type: "codi.qr.payment_received", CodiQRID: "qr-1", TransactionID: "tx-1",
	}

	first, _ := ctrl.RegisterPayment(context.Background(), event)
	second, err := ctrl.RegisterPayment(context.Background(), event)
	if err != nil {
		t.Fatalf("a retry must not error: %v", err)
	}
	if !first {
		t.Error("the first delivery should have applied")
	}
	if second {
		t.Error("Pey retries; the second delivery must not apply again")
	}
	if store.charges["qr-1"].Status != types.ChargePaid {
		t.Error("the charge should be paid")
	}
}

func TestNumericReferenceSurvivesWhatItCan(t *testing.T) {
	cases := map[string]string{
		"2471":      "2471",
		"7A2K":      "72", // letters cannot survive a digits-only field
		"ABC":       "0",
		"123456789": "3456789", // seven digits at most
	}
	for in, want := range cases {
		if got := numericReference(in, 7); got != want {
			t.Errorf("numericReference(%q) = %q, want %q", in, got, want)
		}
	}
}

var _ = utils.Cents(0)
