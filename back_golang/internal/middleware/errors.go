// Package middleware turns domain errors into HTTP answers and guards the
// webhook. It is the only place that knows status codes exist.
package middleware

import (
	"errors"
	"log/slog"
	"net/http"

	"github.com/gofiber/fiber/v3"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

// ErrorHandler maps what the controllers raise onto status codes.
func ErrorHandler(c fiber.Ctx, err error) error {
	status, message := http.StatusInternalServerError, "unexpected error"

	var peyErr *types.PeyError
	var testErr *types.TestModeError

	switch {
	case errors.Is(err, types.ErrPeyNotConfigured):
		status, message = http.StatusServiceUnavailable, err.Error()

	case errors.Is(err, types.ErrInvalidSignature):
		status, message = http.StatusUnauthorized, err.Error()

	case errors.Is(err, types.ErrChargeNotFound):
		status, message = http.StatusNotFound, err.Error()

	case errors.As(err, &testErr):
		status, message = http.StatusUnprocessableEntity, testErr.Error()

	case errors.As(err, &peyErr):
		// Pey's body goes to the log, never to the response: it can name the
		// account that receives the money.
		slog.Error("pey call failed", "status", peyErr.Status, "body", peyErr.Body)
		status, message = http.StatusBadGateway, peyErr.Message

	default:
		var fiberErr *fiber.Error
		if errors.As(err, &fiberErr) {
			status, message = fiberErr.Code, fiberErr.Message
		} else {
			slog.Error("unhandled error", "err", err)
		}
	}

	return c.Status(status).JSON(fiber.Map{"error": message})
}
