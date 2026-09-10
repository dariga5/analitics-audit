// Package api — HTTP-ручки.
package api

import (
	"encoding/json"

	"log"
	"net/http"

	"visualization/internal/report"
)

type Handler struct{}

func NewHandler() *Handler {
	return &Handler{}
}

func (h *Handler) Register(mux *http.ServeMux) {
	mux.HandleFunc("/api/compare", h.handleCompare)
	mux.HandleFunc("/api/health", h.handleHealth)
}

// handleCompare принимает multipart-форму с двумя файлами: file_a, file_b.
// Возвращает JSON с результатом сравнения.
func (h *Handler) handleCompare(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if err := r.ParseMultipartForm(10 << 20); err != nil { // 10 MB
		http.Error(w, "cannot parse form: "+err.Error(), http.StatusBadRequest)
		return
	}

	fileA, _, err := r.FormFile("file_a")
	if err != nil {
		http.Error(w, "missing file_a", http.StatusBadRequest)
		return
	}
	defer fileA.Close()

	fileB, _, err := r.FormFile("file_b")
	if err != nil {
		http.Error(w, "missing file_b", http.StatusBadRequest)
		return
	}
	defer fileB.Close()

	rowsA, err := report.ParseCSV(fileA)
	if err != nil {
		http.Error(w, "parse file_a: "+err.Error(), http.StatusBadRequest)
		return
	}
	rowsB, err := report.ParseCSV(fileB)
	if err != nil {
		http.Error(w, "parse file_b: "+err.Error(), http.StatusBadRequest)
		return
	}

	result := report.Compare(rowsA, rowsB)
	writeJSON(w, result)
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
