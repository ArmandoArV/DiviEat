// Command back_golang serves DiviEat's CoDi charges and user authentication.
package main

import (
	"context"
	"log/slog"
	"os"
	"time"

	"github.com/gofiber/fiber/v3"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/classes"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/config"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/controllers"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/middleware"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/repositories"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/routes"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		slog.Error("bad configuration", "err", err)
		os.Exit(1)
	}

	// Short on purpose: this is a liveness probe, not a connection attempt we
	// wait on. A long timeout here makes a dead Mongo look like a hung boot.
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	client, err := mongo.Connect(options.Client().ApplyURI(cfg.MongoURI))
	if err != nil {
		slog.Error("could not build the mongo client", "err", err)
		os.Exit(1)
	}
	defer func() { _ = client.Disconnect(context.Background()) }()

	db := client.Database(cfg.DatabaseName)
	charges := repositories.NewChargeRepository(db)
	users := repositories.NewUserRepository(db)

	// Booting must not depend on Mongo being up: the API comes alive and
	// /health says what is missing. Dying at startup only hides the cause.
	if err := client.Ping(ctx, nil); err != nil {
		slog.Warn("mongo is not answering; persistence will fail until it does", "err", err)
	} else {
		if err := charges.EnsureIndexes(ctx); err != nil {
			slog.Warn("could not create the charge indexes", "err", err)
		}
		if err := users.EnsureIndexes(ctx); err != nil {
			slog.Warn("could not create the user indexes", "err", err)
		}
	}

	if !cfg.PeyConfigured() {
		slog.Warn("PEY_API_KEY is empty; charges will answer 503 until it is set")
	}
	if !cfg.JWTSecretConfigured() {
		slog.Warn("JWT_SECRET is not set; using default development secret")
	}
	if cfg.TestMode {
		slog.Warn("test mode is on: charges above the ceiling are refused",
			"ceiling", cfg.TestMaxAmount.Display(),
			"why", "Pey has no sandbox, these are real charges")
	}

	var verifier *utils.WebhookVerifier
	if v, err := utils.NewWebhookVerifier(cfg.PeyWebhookSecret, constants.WebhookTolerance); err == nil {
		verifier = v
	} else {
		slog.Warn("webhook signatures cannot be verified", "err", err)
	}

	app := fiber.New(fiber.Config{
		AppName:      "DiviEat API",
		ErrorHandler: middleware.ErrorHandler,
	})
	app.Use(middleware.CORS(cfg.CORSAllowOrigins))

	tokens := utils.NewTokenManager(cfg.JWTSecret, constants.AuthTokenTTL)
	auth := controllers.NewAuthController(users, tokens)
	codi := controllers.NewCodiController(
		classes.NewPeyClient(cfg.PeyAPIKey, cfg.PeyBaseURL),
		charges,
		cfg,
	)
	routes.Register(app, codi, auth, tokens, verifier, cfg)

	slog.Info("listening", "port", cfg.Port)
	if err := app.Listen(":" + cfg.Port); err != nil {
		slog.Error("server stopped", "err", err)
		os.Exit(1)
	}
}
