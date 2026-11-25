// Package routes is transport only: it validates, delegates and answers.
package routes

import (
	"encoding/json"
	"log/slog"

	"github.com/gofiber/fiber/v3"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/config"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/controllers"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/middleware"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

func Register(app *fiber.App, codi *controllers.CodiController, verifier *utils.WebhookVerifier, cfg *config.Config) {
	app.Get("/health", func(c fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"ok":            true,
			"peyConfigured": cfg.PeyConfigured(),
			"testMode":      cfg.TestMode,
			"testCeiling":   cfg.TestMaxAmount.Display(),
		})
	})

	codiGroup := app.Group("/codi")

	codiGroup.Post("/charges", func(c fiber.Ctx) error {
		var in models.CreateChargeRequest
		if err := c.Bind().JSON(&in); err != nil {
			return fiber.NewError(fiber.StatusBadRequest, "malformed body")
		}
		if in.Order == "" || in.Diner == "" {
			return fiber.NewError(fiber.StatusBadRequest, "order and diner are required")
		}
		if in.Cents <= 0 {
			return fiber.NewError(fiber.StatusUnprocessableEntity, "cents must be greater than zero")
		}

		charge, err := codi.CreateCharge(c.Context(), in)
		if err != nil {
			return err
		}
		return c.Status(fiber.StatusCreated).JSON(charge)
	})

	codiGroup.Get("/orders/:order/charges", func(c fiber.Ctx) error {
		charges, err := codi.ChargesForOrder(c.Context(), c.Params("order"))
		if err != nil {
			return err
		}
		return c.JSON(charges)
	})

	app.Post("/webhooks/pey/codi", middleware.VerifyWebhook(verifier), func(c fiber.Ctx) error {
		var event models.QRPaymentReceived
		if err := json.Unmarshal(c.Body(), &event); err != nil {
			return fiber.NewError(fiber.StatusBadRequest, "malformed webhook body")
		}

		applied, err := codi.RegisterPayment(c.Context(), event)
		if err != nil {
			return err
		}
		if applied {
			slog.Info("charge paid", "charge", event.CodiQRID, "transaction", event.TransactionID)
		}

		// Always 200. A retry over an already-paid charge is not an error,
		// and answering 4xx would only make Pey insist.
		return c.JSON(fiber.Map{"received": true, "applied": applied})
	})
}
