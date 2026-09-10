// =============================================================
// app.js — сравнение двух отчётов
// =============================================================

const state = {
  fileA: null,
  fileB: null,
  nameA: "Отчёт A",
  nameB: "Отчёт B",
};

// --- DOM ---
const dropA = document.getElementById("dropA");
const dropB = document.getElementById("dropB");
const inputA = document.getElementById("fileA");
const inputB = document.getElementById("fileB");
const nameAEl = document.getElementById("nameA");
const nameBEl = document.getElementById("nameB");
const compareBtn = document.getElementById("compareBtn");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");
const summary = document.getElementById("summary");
const diffBlocks = document.getElementById("diffBlocks");


// =============================================================
// Drag & Drop
// =============================================================

function setupDrop(drop, input, nameEl, slotKey) {
  drop.addEventListener("click", e => {
    if (e.target !== input) input.click();
  });

  input.addEventListener("change", e => {
    const file = e.target.files && e.target.files[0];
    if (file) setFile(slotKey, file, drop, nameEl);
  });

  drop.addEventListener("dragenter", e => {
    e.preventDefault();
    e.stopPropagation();
    drop.classList.add("dragover");
  });

  drop.addEventListener("dragover", e => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    drop.classList.add("dragover");
  });

  drop.addEventListener("dragleave", e => {
    e.preventDefault();
    e.stopPropagation();
    drop.classList.remove("dragover");
  });

  drop.addEventListener("drop", e => {
    e.preventDefault();
    e.stopPropagation();
    drop.classList.remove("dragover");

    const files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length > 0) {
      setFile(slotKey, files[0], drop, nameEl);
    }
  });
}

function setFile(slot, file, drop, nameEl) {
  const key = slot === "a" ? "fileA" : "fileB";
  const nameKey = slot === "a" ? "nameA" : "nameB";
  state[key] = file;
  state[nameKey] = file.name;
  nameEl.textContent = file.name;
  drop.classList.add("loaded");
  updateCompareButton();
  console.log(`[setFile] slot=${slot} name=${file.name} size=${file.size}`);
}

function updateCompareButton() {
  compareBtn.disabled = !(state.fileA && state.fileB);
}

["dragover", "drop"].forEach(ev => {
  window.addEventListener(ev, e => e.preventDefault(), false);
});


// =============================================================
// Compare
// =============================================================

compareBtn.addEventListener("click", async () => {
  if (!state.fileA || !state.fileB) return;

  compareBtn.disabled = true;
  statusEl.textContent = "Сравнение...";
  result.classList.add("hidden");

  try {
    const form = new FormData();
    form.append("file_a", state.fileA);
    form.append("file_b", state.fileB);

    const resp = await fetch("/api/compare", { method: "POST", body: form });
    if (!resp.ok) throw new Error(await resp.text());

    const data = await resp.json();
    renderResult(data);
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = "Ошибка: " + err.message;
  } finally {
    compareBtn.disabled = false;
  }
});


// =============================================================
// Rendering
// =============================================================

const ALL_COLUMNS = [
  "client_id", "project_ids", "project_name", "service_type",
  "term_months", "flight_no", "flight_start", "flight_end",
  "last_active_month", "status", "report_generated_at",
];

function renderResult(data) {
  result.classList.remove("hidden");
  renderSummary(data.summary);
  diffBlocks.innerHTML =
    renderOnlyIn(state.nameA, data.only_in_a, "block--only-a") +
    renderOnlyIn(state.nameB, data.only_in_b, "block--only-b") +
    renderDifferent(data.different);
}

function renderSummary(s) {
  summary.innerHTML = `
    <div>Строк в <b>${esc(state.nameA)}</b>: <b>${s.total_a}</b></div>
    <div>Строк в <b>${esc(state.nameB)}</b>: <b>${s.total_b}</b></div>
    <div>Только в A: <b>${s.only_in_a}</b></div>
    <div>Только в B: <b>${s.only_in_b}</b></div>
    <div>Расхождений: <b>${s.different}</b></div>
    <div>Совпало: <b>${s.same}</b></div>
  `;
}

function renderOnlyIn(fileName, rows, cssClass) {
  if (!rows || rows.length === 0) {
    return `<div class="block block--empty">
      <div class="block__title">Только в «${esc(fileName)}»: нет</div>
    </div>`;
  }

  const header = `<th>строка</th>` +
    ALL_COLUMNS.map(c => `<th>${esc(c)}</th>`).join("");
  const body = rows.map(r => `
    <tr>
      <td class="row-num">${r.row_num ?? "—"}</td>
      ${ALL_COLUMNS.map(c => `<td>${esc(r[c])}</td>`).join("")}
    </tr>
  `).join("");

  return `<div class="block ${cssClass}">
    <div class="block__title">Только в «${esc(fileName)}» (${rows.length})</div>
    <div class="table-wrap">
      <table>
        <thead><tr>${header}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  </div>`;
}

function renderDifferent(rows) {
  if (!rows || rows.length === 0) {
    return `<div class="block block--empty">
      <div class="block__title">Расхождения: нет</div>
    </div>`;
  }

  const items = rows.map(r => {
    const headerCells = r.fields.map(f => `<th>${esc(f.column)}</th>`).join("");

    const valueA = r.fields.map(f =>
      `<td class="cell cell--old">${esc(f.value_a)}</td>`).join("");
    const valueB = r.fields.map(f =>
      `<td class="cell cell--new">${esc(f.value_b)}</td>`).join("");

    return `<div class="row-diff">
      <div class="row-diff__key">
        <span class="row-diff__key-label">${esc(r.key)}</span>
        <span class="row-diff__row-nums">
          строка ${r.row_num_a} в «${esc(state.nameA)}» ·
          строка ${r.row_num_b} в «${esc(state.nameB)}»
        </span>
      </div>
      <div class="table-wrap">
        <table class="row-diff__table">
          <thead>
            <tr>
              <th class="row-diff__label">файл</th>
              <th class="row-diff__label">№</th>
              ${headerCells}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="row-diff__label row-diff__label--a">${esc(state.nameA)}</td>
              <td class="row-diff__label row-diff__label--a">${r.row_num_a}</td>
              ${valueA}
            </tr>
            <tr>
              <td class="row-diff__label row-diff__label--b">${esc(state.nameB)}</td>
              <td class="row-diff__label row-diff__label--b">${r.row_num_b}</td>
              ${valueB}
            </tr>
          </tbody>
        </table>
      </div>
    </div>`;
  }).join("");

  return `<div class="block block--diff">
    <div class="block__title">Расхождения (${rows.length})</div>
    ${items}
  </div>`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}


// =============================================================
// Init
// =============================================================

setupDrop(dropA, inputA, nameAEl, "a");
setupDrop(dropB, inputB, nameBEl, "b");

console.log("[init] app.js loaded");