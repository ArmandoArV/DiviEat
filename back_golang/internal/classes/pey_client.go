// Package classes holds the service clients.
//
// The name mirrors the Python backend's layout so that moving between the two
// is not a puzzle; a Go-only codebase would call this `clients`.
package classes

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

// PeyClient is the only piece that knows the shape of the wire. Everything
// leaving it is validated against our models, and everything that fails
// leaves as a *types.PeyError, never as a transport error.
type PeyClient struct {
	apiKey  string
	baseURL string
	http    *http.Client
}

func NewPeyClient(apiKey, baseURL string) *PeyClient {
	if baseURL == "" {
		baseURL = constants.PeyBaseURL
	}
	return &PeyClient{
		apiKey:  apiKey,
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: constants.PeyRequestTimeout},
	}
}

func (c *PeyClient) Configured() bool { return c.apiKey != "" }

// CreateQR calls POST /codi/qr and returns the QR ready to paint.
func (c *PeyClient) CreateQR(ctx context.Context, in models.PeyCreateQR) (*models.PeyQRCreated, error) {
	if !c.Configured() {
		return nil, types.ErrPeyNotConfigured
	}

	body, err := json.Marshal(in)
	if err != nil {
		return nil, &types.PeyError{Message: fmt.Sprintf("could not encode the request: %v", err)}
	}

	req, err := http.NewRequestWithContext(
		ctx, http.MethodPost, c.baseURL+constants.PeyCreateQRPath, bytes.NewReader(body),
	)
	if err != nil {
		return nil, &types.PeyError{Message: fmt.Sprintf("could not build the request: %v", err)}
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	res, err := c.http.Do(req)
	if err != nil {
		return nil, &types.PeyError{Message: fmt.Sprintf("could not reach Pey: %v", err)}
	}
	defer res.Body.Close()

	answer, _ := io.ReadAll(io.LimitReader(res.Body, 1<<20))

	if res.StatusCode != http.StatusCreated {
		return nil, &types.PeyError{
			Message: fmt.Sprintf("Pey answered %d when creating the QR", res.StatusCode),
			Status:  res.StatusCode,
			Body:    string(answer),
		}
	}

	var created models.PeyQRCreated
	if err := json.Unmarshal(answer, &created); err != nil {
		return nil, &types.PeyError{Message: fmt.Sprintf("Pey's answer was unreadable: %v", err)}
	}
	return &created, nil
}
