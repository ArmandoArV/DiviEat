package utils

import (
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

func TestTokenManagerRoundTrip(t *testing.T) {
	mgr := NewTokenManager("super-secret-key", time.Hour)
	fixed := time.Date(2026, 11, 25, 12, 0, 0, 0, time.UTC)
	mgr.now = func() time.Time { return fixed }

	token, err := mgr.Sign(TokenSubject{
		ID:    "usr-1",
		Name:  "Mariana",
		Email: "mariana@divieat.mx",
		Role:  types.RoleComensal,
	})
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	claims, err := mgr.Verify(token)
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	if claims.Sub != "usr-1" || claims.Email != "mariana@divieat.mx" || claims.Role != types.RoleComensal {
		t.Fatalf("unexpected claims: %+v", claims)
	}
}

func TestTokenManagerRejectsTamperedAndExpired(t *testing.T) {
	mgr := NewTokenManager("super-secret-key", time.Minute)
	fixed := time.Date(2026, 11, 25, 12, 0, 0, 0, time.UTC)
	mgr.now = func() time.Time { return fixed }

	token, err := mgr.Sign(TokenSubject{
		ID:    "usr-1",
		Name:  "Mariana",
		Email: "mariana@divieat.mx",
		Role:  types.RoleMesero,
	})
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	parts := strings.Split(token, ".")
	tampered := parts[0] + "." + parts[1] + ".tampered"
	if _, err := mgr.Verify(tampered); !errors.Is(err, types.ErrInvalidToken) {
		t.Errorf("tampered token: got %v, want ErrInvalidToken", err)
	}

	otherKey := NewTokenManager("different-secret", time.Minute)
	otherKey.now = mgr.now
	if _, err := otherKey.Verify(token); !errors.Is(err, types.ErrInvalidToken) {
		t.Errorf("wrong key: got %v, want ErrInvalidToken", err)
	}

	mgr.now = func() time.Time { return fixed.Add(2 * time.Minute) }
	if _, err := mgr.Verify(token); !errors.Is(err, types.ErrInvalidToken) {
		t.Errorf("expired token: got %v, want ErrInvalidToken", err)
	}
}
