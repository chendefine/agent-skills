package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func RequestLogger() gin.HandlerFunc { return gin.Logger() }
func Recovery() gin.HandlerFunc { return gin.Recovery() }

func CORS(allowedOrigins []string) gin.HandlerFunc {
	allowed := make(map[string]struct{}, len(allowedOrigins))
	allowAll := false
	for _, origin := range allowedOrigins {
		if origin == "*" {
			allowAll = true
		}
		allowed[origin] = struct{}{}
	}
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		_, explicitlyAllowed := allowed[origin]
		if origin != "" && (allowAll || explicitlyAllowed) {
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Access-Control-Allow-Credentials", "true")
			c.Header("Vary", "Origin")
		}
		if c.Request.Method == http.MethodOptions {
			c.Header("Access-Control-Allow-Headers", "Authorization, Content-Type")
			c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	}
}
