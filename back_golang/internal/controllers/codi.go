// Package controllers holds the use cases.
//
// The one translation between cents (ours) and pesos (Pey's) lives here, and
// so does the test-mode brake. Neither belongs in a route: they are rules,
// not transport.
package controllers

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/classes"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/config"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/repositories"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

type CodiController struct {
	pey     *classes.PeyClient
	charges repositories.ChargeStore
	cfg     *config.Config
}

func NewCodiController(pey *classes.PeyClient, charges repositories.ChargeStore, cfg *config.Config) *CodiController {
	return &CodiController{pey: pey, charges: charges, cfg: cfg}
}

func (c *CodiController) CreateCharge(ctx context.Context, in models.CreateChargeRequest) (*models.ChargeCreated, error) {
	// Pey has no sandbox: this moves real money. While test mode is on, a
	// large amount is almost always a units mistake — cents passed where
	// pesos go, which is a 100x error — rather than an intention.
	if c.cfg.TestMode && in.Cents > c.cfg.TestMaxAmount {
		return nil, &types.TestModeError{
			Amount:  in.Cents.Decimal(),
			Ceiling: c.cfg.TestMaxAmount.Decimal(),
		}
	}

	concept := in.Concept
	if concept == "" {
		concept = "DiviEat - order " + in.Order
	}
	if len(concept) > 120 {
		concept = concept[:120]
	}

	numRef := numericReference(in.Order, constants.PeyNumRefMaxDigits)

	created, err := c.pey.CreateQR(ctx, models.PeyCreateQR{
		Amount:        models.Pesos{Cents: in.Cents},
		Concept:       concept,
		Expiration:    c.cfg.PeyQRExpiry,
		NumRef:        numRef,
		GenerateImage: false,
		BankAccountID: c.cfg.PeyBankAccountID,
		// numRef only takes digits, so the firm link back to our order rides
		// here. This is what the webhook reads.
		Metadata: map[string]string{"order": in.Order, "diner": in.Diner},
	})
	if err != nil {
		return nil, err
	}
	if created.QRString == "" {
		return nil, &types.PeyError{Message: "Pey created the charge but returned no QR payload"}
	}

	id := created.ID
	if id == "" {
		id = randomID()
	}

	charge := models.Charge{
		ID:        id,
		Order:     in.Order,
		Diner:     in.Diner,
		Cents:     in.Cents,
		Status:    types.ChargePending,
		QRString:  created.QRString,
		NumRef:    numRef,
		CreatedAt: time.Now().UTC(),
	}
	if err := c.charges.Save(ctx, charge); err != nil {
		return nil, err
	}

	return &models.ChargeCreated{
		ID:            charge.ID,
		Order:         charge.Order,
		Diner:         charge.Diner,
		Cents:         charge.Cents,
		Amount:        charge.Cents.Display(),
		Status:        charge.Status,
		QRString:      charge.QRString,
		QRImageBase64: created.QRImage,
		ExpiresInSecs: c.cfg.PeyQRExpiry,
	}, nil
}

// RegisterPayment marks the charge paid and reports whether this delivery
// moved anything. False means it was already paid, which is normal when Pey
// retries.
func (c *CodiController) RegisterPayment(ctx context.Context, event models.QRPaymentReceived) (bool, error) {
	if event.Type != constants.PeyQRPaymentEvent {
		return false, nil
	}
	return c.charges.MarkPaid(ctx, event.CodiQRID, event.TransactionID)
}

func (c *CodiController) ChargesForOrder(ctx context.Context, order string) ([]models.Charge, error) {
	return c.charges.ByOrder(ctx, order)
}

// numericReference builds a valid numRef out of any identifier.
//
// Pey takes digits only, seven at most. An order number like "2471" survives
// intact; an alphanumeric one like "7A2K" loses its letters, so what is left
// is a reconciliation hint, not an identifier — the firm link is metadata.
func numericReference(text string, maxDigits int) string {
	digits := make([]rune, 0, len(text))
	for _, r := range text {
		if r >= '0' && r <= '9' {
			digits = append(digits, r)
		}
	}
	if len(digits) == 0 {
		return "0"
	}
	if len(digits) > maxDigits {
		digits = digits[len(digits)-maxDigits:]
	}
	return string(digits)
}

func randomID() string {
	buf := make([]byte, 16)
	_, _ = rand.Read(buf)
	return hex.EncodeToString(buf)
}
