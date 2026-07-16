package service

import (
	"context"
	"errors"
	"testing"
)

type healthCheckerFunc func(context.Context) error

func (f healthCheckerFunc) Ping(ctx context.Context) error { return f(ctx) }

func TestHealthCheck(t *testing.T) {
	result, err := NewHealth(nil).Check(context.Background())
	if err != nil || result.Status != "ok" || result.Service != serviceName {
		t.Fatalf("Check() = %#v, %v", result, err)
	}
}

func TestHealthCheckReportsDatabaseFailure(t *testing.T) {
	want := errors.New("database unavailable")
	_, err := NewHealth(healthCheckerFunc(func(context.Context) error { return want })).Check(context.Background())
	if !errors.Is(err, want) {
		t.Fatalf("Check() error = %v, want wrapped %v", err, want)
	}
}
