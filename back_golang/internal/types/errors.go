package types

import (
	"errors"
	"fmt"
)

// Domain errors. Controllers raise these; the error middleware is the only
// place that decides what each one means over HTTP, so the business logic
// never needs to know a status code exists.
var (
	ErrPeyNotConfigured = errors.New("PEY_API_KEY is empty; create one at portal.mipey.mx/developers")
	ErrChargeNotFound   = errors.New("charge not found")
	ErrInvalidSignature = errors.New("invalid webhook signature")
)

// PeyError wraps anything Pey answered that we cannot use.
type PeyError struct {
	Message string
	Status  int
	// Body stays out of HTTP responses: it can name the receiving account.
	Body string
}

func (e *PeyError) Error() string { return e.Message }

// TestModeError means the spending guard refused the charge before it ever
// reached Pey.
type TestModeError struct {
	Amount  string
	Ceiling string
}

func (e *TestModeError) Error() string {
	return fmt.Sprintf(
		"test mode: %s MXN is above the %s MXN ceiling; turn PEY_TEST_MODE off to charge for real",
		e.Amount, e.Ceiling,
	)
}
