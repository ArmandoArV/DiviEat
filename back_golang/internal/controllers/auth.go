package controllers

import (
	"context"
	"errors"
	"net/mail"
	"strings"
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/repositories"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

type AuthController struct {
	users  repositories.UserStore
	tokens *utils.TokenManager
}

func NewAuthController(users repositories.UserStore, tokens *utils.TokenManager) *AuthController {
	return &AuthController{users: users, tokens: tokens}
}

func (c *AuthController) Register(ctx context.Context, in models.RegisterRequest) (*models.AuthResponse, error) {
	name := strings.TrimSpace(in.Name)
	if name == "" {
		return nil, types.ErrNameRequired
	}

	email, err := normalizeEmail(in.Email)
	if err != nil {
		return nil, err
	}

	if len(in.Password) < constants.MinPasswordLength {
		return nil, types.ErrWeakPassword
	}

	role := in.Role
	if role == "" {
		role = types.RoleComensal
	}
	if !role.Valid() {
		return nil, types.ErrInvalidRole
	}

	if _, err := c.users.ByEmail(ctx, email); err == nil {
		return nil, types.ErrEmailTaken
	} else if !errors.Is(err, types.ErrUserNotFound) {
		return nil, err
	}

	hash, err := utils.HashPassword(in.Password)
	if err != nil {
		return nil, err
	}

	user := models.User{
		ID:        randomID(),
		Name:      name,
		Email:     email,
		Role:      role,
		Password:  hash,
		CreatedAt: time.Now().UTC(),
	}

	if err := c.users.Create(ctx, user); err != nil {
		return nil, err
	}

	return c.issueAuth(user)
}

func (c *AuthController) Login(ctx context.Context, in models.LoginRequest) (*models.AuthResponse, error) {
	email, err := normalizeEmail(in.Email)
	if err != nil || in.Password == "" {
		return nil, types.ErrInvalidCredentials
	}

	user, err := c.users.ByEmail(ctx, email)
	if err != nil {
		if errors.Is(err, types.ErrUserNotFound) {
			return nil, types.ErrInvalidCredentials
		}
		return nil, err
	}

	if !utils.CheckPassword(user.Password, in.Password) {
		return nil, types.ErrInvalidCredentials
	}

	return c.issueAuth(*user)
}

func (c *AuthController) Me(ctx context.Context, userID string) (*models.UserPublic, error) {
	user, err := c.users.ByID(ctx, userID)
	if err != nil {
		return nil, err
	}
	pub := user.Public()
	return &pub, nil
}

func (c *AuthController) issueAuth(user models.User) (*models.AuthResponse, error) {
	pub := user.Public()
	token, err := c.tokens.Sign(utils.TokenSubject{
		ID:    pub.ID,
		Name:  pub.Name,
		Email: pub.Email,
		Role:  pub.Role,
	})
	if err != nil {
		return nil, err
	}
	return &models.AuthResponse{
		Token: token,
		User:  pub,
	}, nil
}

func normalizeEmail(raw string) (string, error) {
	trimmed := strings.ToLower(strings.TrimSpace(raw))
	if trimmed == "" {
		return "", types.ErrInvalidEmail
	}
	addr, err := mail.ParseAddress(trimmed)
	if err != nil || addr.Address != trimmed || !strings.Contains(trimmed, ".") {
		return "", types.ErrInvalidEmail
	}
	return trimmed, nil
}
