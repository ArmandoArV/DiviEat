package routes

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gofiber/fiber/v3"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/classes"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/config"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/controllers"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/middleware"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/utils"
)

type stubChargeStore struct{}

func (stubChargeStore) Save(context.Context, models.Charge) error                    { return nil }
func (stubChargeStore) ByOrder(context.Context, string) ([]models.Charge, error)     { return nil, nil }
func (stubChargeStore) MarkPaid(context.Context, string, string) (bool, error)       { return false, nil }

type stubUserStore struct {
	byEmail map[string]models.User
	byID    map[string]models.User
}

func (s *stubUserStore) Create(_ context.Context, user models.User) error {
	if _, ok := s.byEmail[user.Email]; ok {
		return types.ErrEmailTaken
	}
	s.byEmail[user.Email] = user
	s.byID[user.ID] = user
	return nil
}

func (s *stubUserStore) ByEmail(_ context.Context, email string) (*models.User, error) {
	u, ok := s.byEmail[email]
	if !ok {
		return nil, types.ErrUserNotFound
	}
	return &u, nil
}

func (s *stubUserStore) ByID(_ context.Context, id string) (*models.User, error) {
	u, ok := s.byID[id]
	if !ok {
		return nil, types.ErrUserNotFound
	}
	return &u, nil
}

func newTestApp() *fiber.App {
	cfg := &config.Config{
		JWTSecret:        "route-test-secret",
		CORSAllowOrigins: "http://localhost:3000",
	}
	app := fiber.New(fiber.Config{ErrorHandler: middleware.ErrorHandler})
	app.Use(middleware.CORS(cfg.CORSAllowOrigins))

	users := &stubUserStore{byEmail: map[string]models.User{}, byID: map[string]models.User{}}
	tokens := utils.NewTokenManager(cfg.JWTSecret, time.Hour)
	auth := controllers.NewAuthController(users, tokens)
	codi := controllers.NewCodiController(classes.NewPeyClient("", ""), stubChargeStore{}, cfg)

	Register(app, codi, auth, tokens, nil, cfg)
	return app
}

func TestAuthRoutesFlow(t *testing.T) {
	app := newTestApp()

	// CORS preflight
	preflight := httptest.NewRequest(http.MethodOptions, "/auth/login", nil)
	preflight.Header.Set("Origin", "http://localhost:3000")
	resp, err := app.Test(preflight)
	if err != nil {
		t.Fatalf("preflight: %v", err)
	}
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("preflight status = %d, want 204", resp.StatusCode)
	}
	if got := resp.Header.Get("Access-Control-Allow-Origin"); got != "http://localhost:3000" {
		t.Fatalf("Allow-Origin = %q, want http://localhost:3000", got)
	}

	// Register
	regBody := bytes.NewBufferString(`{"name":"Sofía","email":"sofia@divieat.mx","role":"admin","password":"password123"}`)
	regReq := httptest.NewRequest(http.MethodPost, "/auth/register", regBody)
	regReq.Header.Set("Content-Type", "application/json")
	regResp, err := app.Test(regReq)
	if err != nil {
		t.Fatalf("register: %v", err)
	}
	if regResp.StatusCode != http.StatusCreated {
		t.Fatalf("register status = %d, want 201", regResp.StatusCode)
	}
	var regOut models.AuthResponse
	if err := json.NewDecoder(regResp.Body).Decode(&regOut); err != nil {
		t.Fatalf("decode register: %v", err)
	}
	if regOut.Token == "" || regOut.User.Role != types.RoleAdmin {
		t.Fatalf("unexpected register body: %+v", regOut)
	}

	// Duplicate register returns 409
	dupReq := httptest.NewRequest(http.MethodPost, "/auth/register", bytes.NewBufferString(`{"name":"Sofía","email":"sofia@divieat.mx","role":"admin","password":"password123"}`))
	dupReq.Header.Set("Content-Type", "application/json")
	dupResp, err := app.Test(dupReq)
	if err != nil {
		t.Fatalf("duplicate register: %v", err)
	}
	if dupResp.StatusCode != http.StatusConflict {
		t.Fatalf("duplicate status = %d, want 409", dupResp.StatusCode)
	}

	// Login
	loginReq := httptest.NewRequest(http.MethodPost, "/auth/login", bytes.NewBufferString(`{"email":"sofia@divieat.mx","password":"password123"}`))
	loginReq.Header.Set("Content-Type", "application/json")
	loginResp, err := app.Test(loginReq)
	if err != nil {
		t.Fatalf("login: %v", err)
	}
	if loginResp.StatusCode != http.StatusOK {
		t.Fatalf("login status = %d, want 200", loginResp.StatusCode)
	}

	// GET /auth/me with Bearer token
	meReq := httptest.NewRequest(http.MethodGet, "/auth/me", nil)
	meReq.Header.Set("Authorization", "Bearer "+regOut.Token)
	meResp, err := app.Test(meReq)
	if err != nil {
		t.Fatalf("me: %v", err)
	}
	if meResp.StatusCode != http.StatusOK {
		t.Fatalf("me status = %d, want 200", meResp.StatusCode)
	}

	// GET /auth/me without token -> 401
	unauthResp, err := app.Test(httptest.NewRequest(http.MethodGet, "/auth/me", nil))
	if err != nil {
		t.Fatalf("unauth me: %v", err)
	}
	if unauthResp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("unauth status = %d, want 401", unauthResp.StatusCode)
	}
}
