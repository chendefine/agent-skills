package model

import (
	"time"

	"gorm.io/gorm"
)

// Base contains persistence fields shared by ordinary GORM models.
type Base struct {
	ID        uint `gorm:"primaryKey"`
	CreatedAt time.Time
	UpdatedAt time.Time
	DeletedAt gorm.DeletedAt `gorm:"index"`
}
