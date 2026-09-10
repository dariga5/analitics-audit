// Package api регистрирует HTTP-ручки.
package api

import (
	"log"

	"encoding/json"
	"net/http"

	"visualization/internal/report"
)

// Handler держит ссылку на репозиторий и раздаёт данные по HTTP.
type Handler struct {
	repo *report.Repository
}

func NewHandler(repo *report.Repository) *Handler {
	return &Handler{repo: repo}
}

// Register вешает ручки на переданный mux.
func (h *Handler) Register(mux *http.ServeMux) {
	mux.HandleFunc("/api/report", h.handleReport)
	mux.HandleFunc("/api/summary", h.handleSummary)
	mux.HandleFunc("/api/health", h.handleHealth)
}

func (h *Handler) handleReport(w http.ResponseWriter, r *http.Request) {
	rows, err := h.repo.Load()
	if err != nil {
		log.Printf("load report: %v", err)
		http.Error(w, "failed to load report", http.StatusInternalServerError)
		return
	}
	writeJSON(w, rows)
}

func (h *Handler) handleSummary(w http.ResponseWriter, r *http.Request) {
	rows, err := h.repo.Load()
	if err != nil {
		log.Printf("load report: %v", err)
		http.Error(w, "failed to load report", http.StatusInternalServerError)
		return
	}
	writeJSON(w, h.repo.Summarize(rows))
}

func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"status": "ok"})
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode json: %v", err)
	}
}
