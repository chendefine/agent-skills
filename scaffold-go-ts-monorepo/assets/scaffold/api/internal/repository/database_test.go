package repository

import (
	"context"
	"testing"
)

func TestDisabledDatabaseIsSafe(t *testing.T) {
	var database *Database
	if got := database.GORM(); got != nil {
		t.Fatalf("GORM() = %v, want nil", got)
	}
	if err := database.Ping(context.Background()); err != nil {
		t.Fatalf("Ping() error = %v", err)
	}
	if err := database.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}
}
