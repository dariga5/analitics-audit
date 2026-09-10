// Package report отвечает за чтение CSV с отчётом и его агрегацию.
package report

import (
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"encoding/csv"

	"visualization/pkg/models"
)

// Repository читает CSV-файл с отчётом.
type Repository struct {
	path string
}

func NewRepository(path string) *Repository {
	return &Repository{path: path}
}

func (r *Repository) Load() ([]models.ReportRow, error) {
	f, err := os.Open(r.path)
	if err != nil {
		return nil, fmt.Errorf("open report: %w", err)
	}
	defer f.Close()

	reader := csv.NewReader(f)
	reader.Comma = ';'
	reader.FieldsPerRecord = -1 // разрешаем разное число колонок в строках
	reader.LazyQuotes = true

	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	// Убираем BOM в первой колонке (utf-8-sig).
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}

	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}

	required := []string{
		"client_id", "project_ids", "project_name", "service_type",
		"term_months", "flight_no", "flight_start", "flight_end",
		"last_active_month", "status", "report_generated_at",
	}
	for _, col := range required {
		if _, ok := idx[col]; !ok {
			return nil, fmt.Errorf("missing column: %s", col)
		}
	}

	var rows []models.ReportRow
	for {
		rec, err := reader.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(rec) < len(header) {
			continue // битая строка — пропускаем
		}

		term, _ := strconv.Atoi(strings.TrimSpace(rec[idx["term_months"]]))
		flightNo, _ := strconv.Atoi(strings.TrimSpace(rec[idx["flight_no"]]))

		rows = append(rows, models.ReportRow{
			ClientID:          strings.TrimSpace(rec[idx["client_id"]]),
			ProjectIDs:        strings.TrimSpace(rec[idx["project_ids"]]),
			ProjectName:       strings.TrimSpace(rec[idx["project_name"]]),
			ServiceType:       strings.TrimSpace(rec[idx["service_type"]]),
			TermMonths:        term,
			FlightNo:          flightNo,
			FlightStart:       strings.TrimSpace(rec[idx["flight_start"]]),
			FlightEnd:         strings.TrimSpace(rec[idx["flight_end"]]),
			LastActiveMonth:   strings.TrimSpace(rec[idx["last_active_month"]]),
			Status:            strings.TrimSpace(rec[idx["status"]]),
			ReportGeneratedAt: strings.TrimSpace(rec[idx["report_generated_at"]]),
		})
	}
	return rows, nil
}

func (r *Repository) Summarize(rows []models.ReportRow) models.Summary {
	s := models.Summary{
		TotalRows: len(rows),
		ByStatus:  map[string]int{},
		ByService: map[string]int{},
	}
	clients := make(map[string]struct{})
	for _, row := range rows {
		clients[row.ClientID] = struct{}{}
		s.ByStatus[row.Status]++
		s.ByService[row.ServiceType]++
	}
	s.TotalClients = len(clients)
	return s
}
