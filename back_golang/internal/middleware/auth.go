package middleware

import (
	"strings"

	"github.com/gofiber/fiber/v3"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

const authClaimsKey = "authClaims"

// RequireAuth verifies the Bearer JWT and attaches the parsed claims to the
// request context.
func RequireAuth(tokens *utils.TokenManager) fiber.Handler {
	return func(c fiber.Ctx) error {
		header := c.Get(constants.HeaderAuthorization)
		if !strings.HasPrefix(header, constants.BearerPrefix) {
			return types.ErrInvalidToken
		}
		rawToken := strings.TrimSpace(strings.TrimPrefix(header, constants.BearerPrefix))
		if rawToken == "" {
			return types.ErrInvalidToken
		}

		claims, err := tokens.Verify(rawToken)
		if err != nil {
			return err
		}

		c.Locals(authClaimsKey, claims)
		return c.Next()
	}
}

// AuthClaims extracts the verified claims placed by RequireAuth.
func AuthClaims(c fiber.Ctx) (*utils.TokenClaims, bool) {
	claims, ok := c.Locals(authClaimsKey).(*utils.TokenClaims)
	return claims, ok && claims != nil
}
