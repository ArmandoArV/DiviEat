package utils

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"strings"
	"time"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

// TokenSubject is the minimal identity embedded into a signed JWT.
type TokenSubject struct {
	ID    string
	Name  string
	Email string
	Role  types.Role
}

// TokenClaims is the payload carried inside a signed JWT.
type TokenClaims struct {
	Sub   string     `json:"sub"`
	Name  string     `json:"name"`
	Email string     `json:"email"`
	Role  types.Role `json:"role"`
	Iat   int64      `json:"iat"`
	Exp   int64      `json:"exp"`
}

type jwtHeader struct {
	Alg string `json:"alg"`
	Typ string `json:"typ"`
}

// TokenManager signs and verifies HS256 JWTs using only the standard library.
type TokenManager struct {
	secret []byte
	ttl    time.Duration
	now    func() time.Time
}

func NewTokenManager(secret string, ttl time.Duration) *TokenManager {
	return &TokenManager{
		secret: []byte(secret),
		ttl:    ttl,
		now:    func() time.Time { return time.Now().UTC() },
	}
}

func (m *TokenManager) Sign(subject TokenSubject) (string, error) {
	if len(m.secret) == 0 {
		return "", errors.New("JWT secret is empty")
	}

	issued := m.now()
	claims := TokenClaims{
		Sub:   subject.ID,
		Name:  subject.Name,
		Email: subject.Email,
		Role:  subject.Role,
		Iat:   issued.Unix(),
		Exp:   issued.Add(m.ttl).Unix(),
	}

	headerBytes, err := json.Marshal(jwtHeader{Alg: "HS256", Typ: "JWT"})
	if err != nil {
		return "", err
	}
	claimsBytes, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}

	unsigned := base64.RawURLEncoding.EncodeToString(headerBytes) + "." +
		base64.RawURLEncoding.EncodeToString(claimsBytes)
	sig := m.signBytes([]byte(unsigned))

	return unsigned + "." + base64.RawURLEncoding.EncodeToString(sig), nil
}

func (m *TokenManager) Verify(token string) (*TokenClaims, error) {
	if len(m.secret) == 0 {
		return nil, types.ErrInvalidToken
	}

	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, types.ErrInvalidToken
	}

	headerRaw, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return nil, types.ErrInvalidToken
	}
	var header jwtHeader
	if err := json.Unmarshal(headerRaw, &header); err != nil || header.Alg != "HS256" {
		return nil, types.ErrInvalidToken
	}

	sig, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return nil, types.ErrInvalidToken
	}
	expected := m.signBytes([]byte(parts[0] + "." + parts[1]))
	if !hmac.Equal(sig, expected) {
		return nil, types.ErrInvalidToken
	}

	claimsRaw, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, types.ErrInvalidToken
	}
	var claims TokenClaims
	if err := json.Unmarshal(claimsRaw, &claims); err != nil {
		return nil, types.ErrInvalidToken
	}
	if claims.Sub == "" || claims.Exp <= m.now().Unix() {
		return nil, types.ErrInvalidToken
	}

	return &claims, nil
}

func (m *TokenManager) signBytes(data []byte) []byte {
	mac := hmac.New(sha256.New, m.secret)
	mac.Write(data)
	return mac.Sum(nil)
}
