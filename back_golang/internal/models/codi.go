// Package models holds the wire and storage shapes.
//
// Ours and Pey's are deliberately separate types. Pey speaks PESOS with its
// own English field names; the domain speaks CENTS. Collapse them into one
// struct and sooner or later someone sends cents where pesos go and charges
// a hundred times too much.
package models

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

// --- our API ------------------------------------------------------------

// CreateChargeRequest is what the front end asks for. Always in cents.
type CreateChargeRequest struct {
	Order   string      `json:"order"`
	Diner   string      `json:"diner"`
	Cents   utils.Cents `json:"cents"`
	Concept string      `json:"concept,omitempty"`
}

// ChargeCreated is what the front end needs to paint the QR.
type ChargeCreated struct {
	ID            string             `json:"id"`
	Order         string             `json:"order"`
	Diner         string             `json:"diner"`
	Cents         utils.Cents        `json:"cents"`
	Amount        string             `json:"amount"`
	Status        types.ChargeStatus `json:"status"`
	QRString      string             `json:"qrString"`
	QRImageBase64 string             `json:"qrImage,omitempty"`
	ExpiresInSecs int                `json:"expiresInSeconds"`
}

// Charge is what lives in Mongo.
type Charge struct {
	ID            string             `bson:"id"            json:"id"`
	Order         string             `bson:"order"         json:"order"`
	Diner         string             `bson:"diner"         json:"diner"`
	Cents         utils.Cents        `bson:"cents"         json:"cents"`
	Status        types.ChargeStatus `bson:"status"        json:"status"`
	QRString      string             `bson:"qrString"      json:"qrString"`
	NumRef        string             `bson:"numRef"        json:"numRef"`
	CreatedAt     time.Time          `bson:"createdAt"     json:"createdAt"`
	PaidAt        *time.Time         `bson:"paidAt,omitempty"        json:"paidAt,omitempty"`
	TransactionID string             `bson:"transactionId,omitempty" json:"transactionId,omitempty"`
}

// --- Pey's wire ---------------------------------------------------------
// Field names are verbatim from Pey's contract. Do not translate them.

// Pesos carries an amount over the wire as a JSON number with two decimals,
// built from integer cents so a float never gets near the money.
type Pesos struct{ Cents utils.Cents }

func (p Pesos) MarshalJSON() ([]byte, error) {
	return []byte(p.Cents.Decimal()), nil
}

func (p *Pesos) UnmarshalJSON(raw []byte) error {
	cents, err := utils.ParseDecimal(strings.Trim(string(raw), `"`))
	if err != nil {
		return err
	}
	p.Cents = cents
	return nil
}

type PeyCreateQR struct {
	Amount        Pesos             `json:"amount"`
	Concept       string            `json:"concept,omitempty"`
	Expiration    int               `json:"expiration"`
	NumRef        string            `json:"numRef,omitempty"`
	GenerateImage bool              `json:"generateImage"`
	BankAccountID string            `json:"bankAccountId,omitempty"`
	Metadata      map[string]string `json:"metadata,omitempty"`
}

// PeyQRCreated is Pey's 201 body. Nothing is marked required upstream, so
// every field is optional here and the controller is what insists on
// QRString: without that payload there is nothing to show.
type PeyQRCreated struct {
	ID       string `json:"id"`
	QRString string `json:"qrString"`
	QRImage  string `json:"qrImage"`
}

var _ json.Marshaler = Pesos{}
