package models

// QRPaymentReceived is the body Pey posts when a CoDi QR payment lands.
//
// More fields arrive than are used (apiKeyId, bankAccountId,
// metadata.trackingKey...). They are accepted and ignored: Pey adding one
// should never take the endpoint down.
type QRPaymentReceived struct {
	Type          string `json:"type"`
	TransactionID string `json:"transactionId"`
	CodiQRID      string `json:"codiQrId"`
	Amount        Pesos  `json:"amount"`
	NumRef        string `json:"numRef"`
	Concept       string `json:"concept"`
	DatePaid      int64  `json:"datePaid"`
	Metadata      struct {
		// numRef only takes digits, so the firm link back to our order
		// travels here, under the keys we set when creating the QR.
		External map[string]string `json:"externalMetadata"`
	} `json:"metadata"`
}

func (w QRPaymentReceived) Order() string { return w.Metadata.External["order"] }
func (w QRPaymentReceived) Diner() string { return w.Metadata.External["diner"] }
