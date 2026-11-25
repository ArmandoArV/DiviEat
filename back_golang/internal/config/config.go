// Package config reads every setting from the environment. No keys in code.
package config

import (
	"fmt"
	"os"
	"strconv"

	"github.com/joho/godotenv"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

type Config struct {
	Port             string
	MongoURI         string
	DatabaseName     string
	JWTSecret        string
	CORSAllowOrigins string

	PeyAPIKey        string
	PeyBaseURL       string
	PeyWebhookSecret string
	PeyBankAccountID string
	PeyQRExpiry      int

	// Pey has no sandbox: charges are real money. While TestMode is on, the
	// backend refuses anything above TestMaxAmount.
	TestMode      bool
	TestMaxAmount utils.Cents
}

func Load() (*Config, error) {
	// A missing .env is fine in a deployed environment, where the real
	// variables come from the process environment.
	_ = godotenv.Load()

	expiry := envInt("PEY_QR_EXPIRATION_SECONDS", 900)
	if expiry != constants.PeyNoExpiry && expiry < constants.PeyMinExpirySecond {
		return nil, fmt.Errorf(
			"PEY_QR_EXPIRATION_SECONDS=%d: Pey rejects anything under %d; use 0 for no expiry",
			expiry, constants.PeyMinExpirySecond,
		)
	}

	ceiling, err := utils.ParseDecimal(env("PEY_TEST_MAX_AMOUNT_MXN", "1"))
	if err != nil {
		return nil, fmt.Errorf("PEY_TEST_MAX_AMOUNT_MXN: %w", err)
	}

	return &Config{
		Port:             env("PORT", "8080"),
		MongoURI:         env("MONGODB_URI", "mongodb://localhost:27017"),
		DatabaseName:     env("DATABASE_NAME", "divieat"),
		JWTSecret:        env("JWT_SECRET", "divieat-dev-jwt-secret"),
		CORSAllowOrigins: env("CORS_ALLOW_ORIGINS", "*"),
		PeyAPIKey:        env("PEY_API_KEY", ""),
		PeyBaseURL:       env("PEY_BASE_URL", constants.PeyBaseURL),
		PeyWebhookSecret: env("PEY_WEBHOOK_SECRET", ""),
		PeyBankAccountID: env("PEY_BANK_ACCOUNT_ID", ""),
		PeyQRExpiry:      expiry,
		TestMode:         env("PEY_TEST_MODE", "true") == "true",
		TestMaxAmount:    ceiling,
	}, nil
}

// PeyConfigured reports whether charges can be created at all.
func (c *Config) PeyConfigured() bool { return c.PeyAPIKey != "" }

// JWTSecretConfigured reports whether JWT_SECRET was provided via env.
func (c *Config) JWTSecretConfigured() bool { return os.Getenv("JWT_SECRET") != "" }

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v, err := strconv.Atoi(os.Getenv(key)); err == nil {
		return v
	}
	return fallback
}
