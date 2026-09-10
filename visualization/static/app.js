// Состояние страницы (единственный источник правды для фильтров).
const state = {
  rows: [],
  filtered: [],
  search: "",
  status: "",
  service: "",
};

async function loadReport() {
  try {
    const [reportRes, summaryRes] = await Promise.all([
      fetch("/api/report"),
      fetch("/api/summary"),
    ]);
    if (!reportRes.ok || !summaryRes.ok) throw new Error("bad response");

    state.rows = await reportRes.json();
    const summary = await summaryRes.json();

    renderSummary(summary);
    setupFilters(state.rows);
    applyFilters();
  } catch (err) {
    document.getElementById("summary").innerHTML =
      `<span style="color:#991b1b">Ошибка загрузки данных: ${err.message}</span>`;
  }
}

function renderSummary(s) {
  const statuses = Object.entries(s.by_status)
    .map(([k, v]) => `${escapeHtml(k)}: <b>${v}</b>`)
    .join(" · ");
  document.getElementById("summary").innerHTML =
    `Всего строк: <b>${s.total_rows}</b> · Клиентов: <b>${s.total_clients}</b> · ${statuses}`;
}

function setupFilters(rows) {
  const statusSel = document.getElementById("statusFilter");
  const serviceSel = document.getElementById("serviceFilter");

  [...new Set(rows.map(r => r.status))].sort().forEach(s => {
    statusSel.insertAdjacentHTML("beforeend",
      `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`);
  });
  [...new Set(rows.map(r => r.service_type))].sort().forEach(s => {
    serviceSel.insertAdjacentHTML("beforeend",
      `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`);
  });

  document.getElementById("search").addEventListener("input", e => {
    state.search = e.target.value.trim().toLowerCase();
    applyFilters();
  });
  statusSel.addEventListener("change", e => { state.status = e.target.value; applyFilters(); });
  serviceSel.addEventListener("change", e => { state.service = e.target.value; applyFilters(); });
  document.getElementById("resetBtn").addEventListener("click", () => {
    state.search = ""; state.status = ""; state.service = "";
    document.getElementById("search").value = "";
    statusSel.value = "";
    serviceSel.value = "";
    applyFilters();
  });
}

function applyFilters() {
  const { rows, search, status, service } = state;
  state.filtered = rows.filter(r => {
    if (status && r.status !== status) return false;
    if (service && r.service_type !== service) return false;
    if (search) {
      const hay = `${r.client_id} ${r.project_name} ${r.project_ids} ${r.service_type}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });
  renderTable(state.filtered);
}

// Возвращает CSS-класс для плашки статуса.
function statusClass(status) {
  const s = status.toLowerCase();
  if (s.includes("непролонгировано")) return "status--непролонгировано";
  if (s.includes("пролонгировано"))   return "status--пролонгировано";
  if (s.includes("отвал"))            return "status--отвал";
  if (s.includes("неизвестно"))       return "status--неизвестно";
  return "status--разовые";
}

function renderTable(rows) {
  const tbody = document.querySelector("#reportTable tbody");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#6b7280">Нет данных</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${escapeHtml(r.client_id)}</td>
      <td title="${escapeHtml(r.project_ids)}">${escapeHtml(r.project_name)}</td>
      <td>${escapeHtml(r.service_type)}</td>
      <td>${r.term_months}</td>
      <td>${r.flight_no}</td>
      <td>${r.flight_start}</td>
      <td>${r.flight_end}</td>
      <td>${r.last_active_month}</td>
      <td><span class="status ${statusClass(r.status)}">${escapeHtml(r.status)}</span></td>
    </tr>
  `).join("");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

loadReport();