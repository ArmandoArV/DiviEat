package utils

import "testing"

func TestHashAndCheckPassword(t *testing.T) {
	hash, err := HashPassword("secreto123")
	if err != nil {
		t.Fatalf("HashPassword: %v", err)
	}
	if hash == "secreto123" {
		t.Fatal("password must never be stored in plaintext")
	}
	if !CheckPassword(hash, "secreto123") {
		t.Error("expected matching password to pass")
	}
	if CheckPassword(hash, "otra-clave") {
		t.Error("expected wrong password to fail")
	}
}
