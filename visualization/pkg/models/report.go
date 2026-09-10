// Package models содержит структуры данных, разделяемые между слоями.
package models

// ReportRow — одна строка итогового отчёта.
// JSON-теги совпадают с именами колонок в CSV — фронту удобно.
type ReportRow struct {
	ClientID          string `json:"client_id"`
	ProjectIDs        string `json:"project_ids"`
	ProjectName       string `json:"project_name"`
	ServiceType       string `json:"service_type"`
	TermMonths        int    `json:"term_months"`
	FlightNo          int    `json:"flight_no"`
	FlightStart       string `json:"flight_start"`
	FlightEnd         string `json:"flight_end"`
	LastActiveMonth   string `json:"last_active_month"`
	Status            string `json:"status"`
	ReportGeneratedAt string `json:"report_generated_at"`
}

// Summary — агрегаты по отчёту для верхней панели.
type Summary struct {
	TotalRows    int            `json:"total_rows"`
	TotalClients int            `json:"total_clients"`
	ByStatus     map[string]int `json:"by_status"`
	ByService    map[string]int `json:"by_service"`
}
