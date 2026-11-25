package middleware

import (
	"net/http"
	"strings"

	"github.com/gofiber/fiber/v3"
)

// CORS allows the Next.js webapp to call the API directly from the browser.
func CORS(allowOrigins string) fiber.Handler {
	allowed := make([]string, 0)
	for _, origin := range strings.Split(allowOrigins, ",") {
		if trimmed := strings.TrimSpace(origin); trimmed != "" {
			allowed = append(allowed, trimmed)
		}
	}
	if len(allowed) == 0 {
		allowed = []string{"*"}
	}

	return func(c fiber.Ctx) error {
		origin := c.Get("Origin")
		if origin != "" {
			if match := resolveOrigin(origin, allowed); match != "" {
				c.Set("Access-Control-Allow-Origin", match)
				c.Set("Vary", "Origin")
			}
		} else if allowed[0] == "*" {
			c.Set("Access-Control-Allow-Origin", "*")
		}

		c.Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
		c.Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Method() == http.MethodOptions {
			return c.SendStatus(http.StatusNoContent)
		}
		return c.Next()
	}
}

func resolveOrigin(origin string, allowed []string) string {
	for _, candidate := range allowed {
		if candidate == "*" {
			return "*"
		}
		if candidate == origin {
			return origin
		}
	}
	return ""
}
