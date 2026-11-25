package models

import (
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

// User is the document stored in Mongo. Password holds the bcrypt hash and is
// never serialised onto the wire.
type User struct {
	ID        string     `bson:"id"        json:"id"`
	Name      string     `bson:"name"      json:"name"`
	Email     string     `bson:"email"     json:"email"`
	Role      types.Role `bson:"role"      json:"role"`
	Password  string     `bson:"password"  json:"-"`
	CreatedAt time.Time  `bson:"createdAt" json:"createdAt"`
}

// Public strips the password hash before a user crosses the HTTP boundary.
func (u User) Public() UserPublic {
	return UserPublic{
		ID:        u.ID,
		Name:      u.Name,
		Email:     u.Email,
		Role:      u.Role,
		CreatedAt: u.CreatedAt,
	}
}

// UserPublic is the wire representation of a user.
type UserPublic struct {
	ID        string     `json:"id"`
	Name      string     `json:"name"`
	Email     string     `json:"email"`
	Role      types.Role `json:"role"`
	CreatedAt time.Time  `json:"createdAt"`
}

// RegisterRequest is the payload sent to POST /auth/register.
type RegisterRequest struct {
	Name     string     `json:"name"`
	Email    string     `json:"email"`
	Role     types.Role `json:"role"`
	Password string     `json:"password"`
}

// LoginRequest is the payload sent to POST /auth/login.
type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// AuthResponse is returned by both register and login.
type AuthResponse struct {
	Token string     `json:"token"`
	User  UserPublic `json:"user"`
}
