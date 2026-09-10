package report

import (
	"encoding/csv"

	"errors"
	"fmt"
	"io"
	"strings"

	"visualization/pkg/models"
)

// ParseCSV читает отчёт из потока.
// Разделитель ';', UTF-8 с BOM, первая строка — заголовок.
// Нумерует строки данных с 1 (заголовок не считается).
func ParseCSV(r io.Reader) ([]models.ReportRow, error) {
	reader := csv.NewReader(r)
	reader.Comma = ';'
	reader.FieldsPerRecord = -1
	reader.LazyQuotes = true

	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}

	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}

	var rows []models.ReportRow
	rowNum := 0
	for {
		rec, err := reader.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}

		rowNum++
		get := func(col string) string {
			i, ok := idx[col]
			if !ok || i >= len(rec) {
				return ""
			}
			return strings.TrimSpace(rec[i])
		}

		rows = append(rows, models.ReportRow{
			RowNum:            rowNum,
			ClientID:          get("client_id"),
			ProjectIDs:        get("project_ids"),
			ProjectName:       get("project_name"),
			ServiceType:       get("service_type"),
			TermMonths:        get("term_months"),
			FlightNo:          get("flight_no"),
			FlightStart:       get("flight_start"),
			FlightEnd:         get("flight_end"),
			LastActiveMonth:   get("last_active_month"),
			Status:            get("status"),
			ReportGeneratedAt: get("report_generated_at"),
		})
	}
	return rows, nil
}
