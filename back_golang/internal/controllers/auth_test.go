package controllers

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

type memoryUserStore struct {
	byEmail map[string]models.User
	byID    map[string]models.User
}

func newUserStore() *memoryUserStore {
	return &memoryUserStore{
		byEmail: map[string]models.User{},
		byID:    map[string]models.User{},
	}
}

func (s *memoryUserStore) Create(_ context.Context, user models.User) error {
	if _, exists := s.byEmail[user.Email]; exists {
		return types.ErrEmailTaken
	}
	s.byEmail[user.Email] = user
	s.byID[user.ID] = user
	return nil
}

func (s *memoryUserStore) ByEmail(_ context.Context, email string) (*models.User, error) {
	u, ok := s.byEmail[email]
	if !ok {
		return nil, types.ErrUserNotFound
	}
	return &u, nil
}

func (s *memoryUserStore) ByID(_ context.Context, id string) (*models.User, error) {
	u, ok := s.byID[id]
	if !ok {
		return nil, types.ErrUserNotFound
	}
	return &u, nil
}

func TestRegisterLoginAndMe(t *testing.T) {
	store := newUserStore()
	tokens := utils.NewTokenManager("test-secret", time.Hour)
	ctrl := NewAuthController(store, tokens)

	reg, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name:     "  Mariana López  ",
		Email:    "Mariana@DiviEat.mx",
		Role:     types.RoleMesero,
		Password: "password123",
	})
	if err != nil {
		t.Fatalf("Register: %v", err)
	}
	if reg.Token == "" {
		t.Fatal("expected JWT token on register")
	}
	if reg.User.Name != "Mariana López" || reg.User.Email != "mariana@divieat.mx" || reg.User.Role != types.RoleMesero {
		t.Fatalf("unexpected registered user: %+v", reg.User)
	}

	login, err := ctrl.Login(context.Background(), models.LoginRequest{
		Email:    "MARIANA@DIVIEAT.MX",
		Password: "password123",
	})
	if err != nil {
		t.Fatalf("Login: %v", err)
	}
	if login.User.ID != reg.User.ID || login.Token == "" {
		t.Fatalf("unexpected login response: %+v", login)
	}

	me, err := ctrl.Me(context.Background(), reg.User.ID)
	if err != nil {
		t.Fatalf("Me: %v", err)
	}
	if me.Email != "mariana@divieat.mx" {
		t.Errorf("Me email = %q", me.Email)
	}
}

func TestRegisterValidationAndDuplicates(t *testing.T) {
	store := newUserStore()
	tokens := utils.NewTokenManager("test-secret", time.Hour)
	ctrl := NewAuthController(store, tokens)

	if _, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "", Email: "a@b.com", Role: types.RoleComensal, Password: "password123",
	}); !errors.Is(err, types.ErrNameRequired) {
		t.Errorf("empty name: got %v, want ErrNameRequired", err)
	}

	if _, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "Ana", Email: "not-an-email", Role: types.RoleComensal, Password: "password123",
	}); !errors.Is(err, types.ErrInvalidEmail) {
		t.Errorf("invalid email: got %v, want ErrInvalidEmail", err)
	}

	if _, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "Ana", Email: "ana@b.com", Role: types.RoleComensal, Password: "short",
	}); !errors.Is(err, types.ErrWeakPassword) {
		t.Errorf("short password: got %v, want ErrWeakPassword", err)
	}

	if _, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "Ana", Email: "ana@b.com", Role: "chef", Password: "password123",
	}); !errors.Is(err, types.ErrInvalidRole) {
		t.Errorf("invalid role: got %v, want ErrInvalidRole", err)
	}

	if _, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "Ana", Email: "ana@b.com", Password: "password123",
	}); err != nil {
		t.Fatalf("default role register failed: %v", err)
	}

	if _, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "Otra Ana", Email: "ANA@B.COM", Role: types.RoleAdmin, Password: "password123",
	}); !errors.Is(err, types.ErrEmailTaken) {
		t.Errorf("duplicate email: got %v, want ErrEmailTaken", err)
	}
}

func TestLoginRejectsWrongCredentials(t *testing.T) {
	store := newUserStore()
	tokens := utils.NewTokenManager("test-secret", time.Hour)
	ctrl := NewAuthController(store, tokens)

	_, err := ctrl.Register(context.Background(), models.RegisterRequest{
		Name: "Luis", Email: "luis@divieat.mx", Role: types.RoleComensal, Password: "password123",
	})
	if err != nil {
		t.Fatalf("Register: %v", err)
	}

	if _, err := ctrl.Login(context.Background(), models.LoginRequest{
		Email: "luis@divieat.mx", Password: "wrong-password",
	}); !errors.Is(err, types.ErrInvalidCredentials) {
		t.Errorf("wrong password: got %v, want ErrInvalidCredentials", err)
	}

	if _, err := ctrl.Login(context.Background(), models.LoginRequest{
		Email: "missing@divieat.mx", Password: "password123",
	}); !errors.Is(err, types.ErrInvalidCredentials) {
		t.Errorf("unknown email: got %v, want ErrInvalidCredentials", err)
	}
}
