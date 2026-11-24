// Package types holds domain enums and errors, with no transport knowledge.
package types

// ChargeStatus is the life cycle of a CoDi charge from the moment its QR is
// generated.
type ChargeStatus string

const (
	ChargePending ChargeStatus = "pending"
	ChargePaid    ChargeStatus = "paid"
	ChargeExpired ChargeStatus = "expired"
)
