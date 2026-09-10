package main

import (
	"flag"
	"log"
	"os"

	"net/http"
	"path/filepath"

	"visualization/internal/api"
	"visualization/internal/report"
)

func main() {
	var (
		addr      = flag.String("addr", ":8080", "адрес сервера")
		dataPath  = flag.String("data", "", "путь к CSV-отчёту (по умолчанию ищется в source-data)")
		staticDir = flag.String("static", "", "путь к папке static (по умолчанию ищется автоматически)")
	)
	flag.Parse()

	if *dataPath == "" {
		*dataPath = findDefaultData()
	}
	if *staticDir == "" {
		*staticDir = findDefaultStatic()
	}

	log.Printf("data:   %s", *dataPath)
	log.Printf("static: %s", *staticDir)

	repo := report.NewRepository(*dataPath)
	h := api.NewHandler(repo)

	mux := http.NewServeMux()
	h.Register(mux)
	mux.Handle("/", http.FileServer(http.Dir(*staticDir)))

	srv := &http.Server{
		Addr:    *addr,
		Handler: logMiddleware(mux),
	}

	log.Printf("server started on %s", *addr)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

// findDefaultData ищет CSV в типовых местах.
// Сервис запускается либо из visualization/, либо из корня проекта.
func findDefaultData() string {
	candidates := []string{
		"../source-data/report_fixed.csv",
		"../source-data/report.csv",
		"source-data/report_fixed.csv",
		"source-data/report.csv",
		"report_fixed.csv",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return "../source-data/report.csv"
}

func findDefaultStatic() string {
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

// logMiddleware — простой лог запросов.
func logMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
