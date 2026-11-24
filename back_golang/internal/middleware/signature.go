package middleware

import (
	"fmt"

	"github.com/gofiber/fiber/v3"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

// VerifyWebhook refuses anything Pey did not sign.
//
// Without it, anyone who learns the URL could mark bills as paid. The check
// runs on the raw bytes, before the body is interpreted, because nothing in
// that body is trustworthy until the signature matches.
func VerifyWebhook(verifier *utils.WebhookVerifier) fiber.Handler {
	return func(c fiber.Ctx) error {
		if verifier == nil {
			return fmt.Errorf("%w: PEY_WEBHOOK_SECRET is not set", types.ErrInvalidSignature)
		}
		err := verifier.Verify(
			c.Body(),
			c.Get(constants.HeaderWebhookID),
			c.Get(constants.HeaderWebhookTimestamp),
			c.Get(constants.HeaderWebhookSignature),
		)
		if err != nil {
			return fmt.Errorf("%w: %s", types.ErrInvalidSignature, err)
		}
		return c.Next()
	}
}
