package constants

import "time"

// Auth contract constants.
const (
	UsersCollection = "users"

	MinPasswordLength = 8
	AuthTokenTTL      = 24 * time.Hour

	HeaderAuthorization = "Authorization"
	BearerPrefix        = "Bearer "
)
