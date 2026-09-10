package models

type ReportRow struct {
	RowNum            int    `json:"row_num"` // ← новое: номер строки в файле (данные с 1)
	ClientID          string `json:"client_id"`
	ProjectIDs        string `json:"project_ids"`
	ProjectName       string `json:"project_name"`
	ServiceType       string `json:"service_type"`
	TermMonths        string `json:"term_months"`
	FlightNo          string `json:"flight_no"`
	FlightStart       string `json:"flight_start"`
	FlightEnd         string `json:"flight_end"`
	LastActiveMonth   string `json:"last_active_month"`
	Status            string `json:"status"`
	ReportGeneratedAt string `json:"report_generated_at"`
}

func Columns() []string {
	return []string{
		"client_id", "project_ids", "project_name",
		"service_type", "term_months", "flight_no",
		"flight_start", "flight_end", "last_active_month",
		"status", "report_generated_at",
	}
}

type FieldDifference struct {
	Column string `json:"column"`
	ValueA string `json:"value_a"`
	ValueB string `json:"value_b"`
}

type RowDiff struct {
	Key     string            `json:"key"`
	RowNumA int               `json:"row_num_a"` // ← новое
	RowNumB int               `json:"row_num_b"` // ← новое
	Fields  []FieldDifference `json:"fields"`
}

type CompareResult struct {
	OnlyInA   []ReportRow    `json:"only_in_a"`
	OnlyInB   []ReportRow    `json:"only_in_b"`
	Different []RowDiff      `json:"different"`
	Summary   CompareSummary `json:"summary"`
}

type CompareSummary struct {
	TotalA    int `json:"total_a"`
	TotalB    int `json:"total_b"`
	OnlyInA   int `json:"only_in_a"`
	OnlyInB   int `json:"only_in_b"`
	Different int `json:"different"`
	Same      int `json:"same"`
}
