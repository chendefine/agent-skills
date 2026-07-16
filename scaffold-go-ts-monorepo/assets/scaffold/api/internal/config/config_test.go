package config

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestLoadFileAndEnvironmentOverride(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte("server:\n  address: :8081\n  shutdown_timeout: 3s\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CONFIG_FILE", path)
	t.Setenv("PORT", "9090")
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Server.Address != ":9090" || cfg.Server.ShutdownTimeout != 3*time.Second {
		t.Fatalf("Server = %#v", cfg.Server)
	}
}

func TestLoadWithoutFileUsesDefaults(t *testing.T) {
	t.Chdir(t.TempDir())
	t.Setenv("CONFIG_FILE", "")
	t.Setenv("PORT", "")
	original := defaultConfigFiles
	defaultConfigFiles = []string{"config.yaml"}
	t.Cleanup(func() { defaultConfigFiles = original })
	cfg, err := Load()
	if err != nil || cfg.Server.Address != defaultAddress || cfg.ConfigFile != "" {
		t.Fatalf("Config = %#v, error = %v", cfg, err)
	}
}

func TestLoadRejectsInvalidPoolLimits(t *testing.T) {
	t.Chdir(t.TempDir())
	t.Setenv("CONFIG_FILE", "")
	t.Setenv("DATABASE_MAX_IDLE_CONNS", "10")
	t.Setenv("DATABASE_MAX_OPEN_CONNS", "5")
	if _, err := Load(); err == nil {
		t.Fatal("Load() error = nil")
	}
}
