package main
import "net/http"
func searchHandler(c *gin.Context) {
	http.Get("https://api.example.com")
}
