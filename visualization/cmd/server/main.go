// Точка входа: поднимает HTTP-сервер с API и статикой.
//
// Запуск:
//
//	cd visualization
//	go run ./cmd/server
package main

import (
	"path/filepath"

	"flag"
	"log"
	"net/http"
	"os"

	"visualization/internal/api"
)

func main() {
	var (
		addr      = flag.String("addr", ":8080", "адрес сервера")
		staticDir = flag.String("static", "", "папка static (по умолчанию ищется автоматически)")
	)
	flag.Parse()

	if *staticDir == "" {
		*staticDir = findStatic()
	}
	log.Printf("static: %s", *staticDir)

	mux := http.NewServeMux()
	api.NewHandler().Register(mux)
	mux.Handle("/", http.FileServer(http.Dir(*staticDir)))

	log.Printf("server started on %s", *addr)
	if err := http.ListenAndServe(*addr, logMiddleware(mux)); err != nil {
		log.Fatal(err)
	}
}

func findStatic() string {
	candidates := []string{
		"static",
		"visualization/static",
		filepath.Join("..", "..", "static"),
	}
	for _, c := range candidates {
		if fi, err := os.Stat(c); err == nil && fi.IsDir() {
			return c
		}
	}
	return "static"
}

func logMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
