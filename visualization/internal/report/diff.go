package report

import (
	"fmt"

	"visualization/pkg/models"
)

func rowKey(r models.ReportRow) string {
	return fmt.Sprintf("%s|%s|%s", r.ClientID, r.ProjectIDs, r.FlightNo)
}

func rowToMap(r models.ReportRow) map[string]string {
	return map[string]string{
		"client_id":           r.ClientID,
		"project_ids":         r.ProjectIDs,
		"project_name":        r.ProjectName,
		"service_type":        r.ServiceType,
		"term_months":         r.TermMonths,
		"flight_no":           r.FlightNo,
		"flight_start":        r.FlightStart,
		"flight_end":          r.FlightEnd,
		"last_active_month":   r.LastActiveMonth,
		"status":              r.Status,
		"report_generated_at": r.ReportGeneratedAt,
	}
}

func Compare(a, b []models.ReportRow) models.CompareResult {
	mapA := make(map[string]models.ReportRow, len(a))
	mapB := make(map[string]models.ReportRow, len(b))

	for _, r := range a {
		mapA[rowKey(r)] = r
	}
	for _, r := range b {
		mapB[rowKey(r)] = r
	}

	result := models.CompareResult{
		OnlyInA:   []models.ReportRow{},
		OnlyInB:   []models.ReportRow{},
		Different: []models.RowDiff{},
	}

	for key, rowA := range mapA {
		rowB, ok := mapB[key]
		if !ok {
			result.OnlyInA = append(result.OnlyInA, rowA)
			continue
		}
		fields := diffFields(rowA, rowB)
		if len(fields) > 0 {
			result.Different = append(result.Different, models.RowDiff{
				Key:     key,
				RowNumA: rowA.RowNum,
				RowNumB: rowB.RowNum,
				Fields:  fields,
			})
		}
	}

	for key, rowB := range mapB {
		if _, ok := mapA[key]; !ok {
			result.OnlyInB = append(result.OnlyInB, rowB)
		}
	}

	result.Summary = models.CompareSummary{
		TotalA:    len(a),
		TotalB:    len(b),
		OnlyInA:   len(result.OnlyInA),
		OnlyInB:   len(result.OnlyInB),
		Different: len(result.Different),
		Same:      len(mapA) - len(result.OnlyInA) - len(result.Different),
	}

	return result
}

func diffFields(a, b models.ReportRow) []models.FieldDifference {
	mapA := rowToMap(a)
	mapB := rowToMap(b)

	var diffs []models.FieldDifference
	for _, col := range models.Columns() {
		if mapA[col] != mapB[col] {
			diffs = append(diffs, models.FieldDifference{
				Column: col,
				ValueA: mapA[col],
				ValueB: mapB[col],
			})
		}
	}
	return diffs
}
