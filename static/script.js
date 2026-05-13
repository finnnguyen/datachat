let sessionId = null;
let isUploading = false;

// ── Drop zone setup ────────────────────────────────────────────────────────────
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("click", (e) => e.stopPropagation());
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", async (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) await uploadFile(file);
});
fileInput.addEventListener("change", async () => {
  if (fileInput.files[0]) await uploadFile(fileInput.files[0]);
  fileInput.value = "";  // reset so the same file can be re-uploaded if needed
});

// ── Load sample CSV ─────────────────────────────────────────────────────────────
async function loadSample(name) {
  if (isUploading) return;
  showUploadStatus(`Loading ${name}.csv…`, false);
  try {
    const res = await fetch(`/data/samples/${name}.csv`);
    if (!res.ok) throw new Error("Sample not found");
    const blob = await res.blob();
    const file = new File([blob], `${name}.csv`, { type: "text/csv" });
    await uploadFile(file);
  } catch (e) {
    showUploadStatus(`Could not load sample: ${e.message}`, true);
    isUploading = false;
  }
}

// ── Upload CSV ──────────────────────────────────────────────────────────────────
async function uploadFile(file) {
  if (isUploading) return;
  if (!file.name.toLowerCase().endsWith(".csv")) {
    showUploadStatus("Please choose a .csv file.", true);
    return;
  }

  isUploading = true;
  const label = document.getElementById("drop-label");
  label.textContent = `Uploading ${file.name}…`;
  showUploadStatus("", false);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (data.error) {
      label.textContent = "Drag & drop a CSV here, or click to browse";
      showUploadStatus(data.error, true);
      isUploading = false;
      return;
    }

    sessionId = data.session_id;
    label.textContent = `✓ ${file.name} loaded`;
    showUploadStatus(`Dataset ready: ${data.table_name}`, false);
    renderSchema(data.table_name, data.columns);
  } catch (e) {
    label.textContent = "Drag & drop a CSV here, or click to browse";
    showUploadStatus("Upload failed. Is the server running?", true);
  } finally {
    isUploading = false;
  }
}

function showUploadStatus(msg, isError) {
  const box = document.getElementById("upload-status");
  if (!msg) { box.hidden = true; return; }
  box.hidden = false;
  box.textContent = msg;
  box.style.color = isError ? "#c53030" : "#276749";
  box.style.background = isError ? "#fff5f5" : "#f0fff4";
  box.style.borderColor = isError ? "#feb2b2" : "#9ae6b4";
}

// ── Render schema ───────────────────────────────────────────────────────────────
function renderSchema(tableName, columns) {
  document.getElementById("schema-table-name").textContent = tableName;
  const tagsEl = document.getElementById("schema-columns");
  tagsEl.innerHTML = "";
  columns.forEach((col) => {
    const tag = document.createElement("span");
    tag.className = "col-tag";
    tag.innerHTML = `${col.name}<span class="col-type">${col.type}</span>`;
    tagsEl.appendChild(tag);
  });
  document.getElementById("schema-section").hidden = false;
  document.getElementById("query-section").hidden = false;
  document.getElementById("result-section").hidden = false;
  document.getElementById("question-input").focus();
}

// ── Submit question ─────────────────────────────────────────────────────────────
async function submitQuestion() {
  const input = document.getElementById("question-input");
  const question = input.value.trim();
  if (!question) { input.focus(); return; }
  if (!sessionId) {
    showError("Please upload a CSV first.");
    return;
  }

  setLoading(true);
  clearResult();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  try {
    const res = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const data = await res.json();
    setLoading(false);

    if (data.error) {
      showError(data.error);
      if (data.sql) renderSQL(data.sql);
      return;
    }

    renderAnswer(data);
  } catch (e) {
    clearTimeout(timeout);
    setLoading(false);
    if (e.name === "AbortError") {
      showError("Request timed out after 60 seconds. The server may be overloaded — try again.");
    } else {
      showError("Request failed. Is the server running?");
    }
  }
}

// Allow Enter key in the question input
document.getElementById("question-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitQuestion();
});

// ── Render helpers ──────────────────────────────────────────────────────────────
function setLoading(on) {
  document.getElementById("loading").hidden = !on;
  document.getElementById("ask-btn").disabled = on;
}

function clearResult() {
  document.getElementById("error-box").hidden = true;
  document.getElementById("answer-box").hidden = true;
  document.getElementById("chart-box").hidden = true;
  document.getElementById("table-box").hidden = true;
  document.getElementById("result-table").innerHTML = "";
}

function showError(msg) {
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.hidden = false;
}

function renderSQL(sql) {
  document.getElementById("sql-display").textContent = sql;
  document.getElementById("answer-box").hidden = false;
}

function renderAnswer(data) {
  // Answer text
  document.getElementById("answer-text").textContent = data.answer;
  renderSQL(data.sql);

  // Chart
  if (data.chart_b64) {
    document.getElementById("chart-img").src = `data:image/png;base64,${data.chart_b64}`;
    document.getElementById("chart-box").hidden = false;
  }

  // Table
  if (data.rows && data.rows.length > 0) {
    buildTable(data.rows);
    document.getElementById("row-count").textContent = data.rows.length;
    document.getElementById("table-box").hidden = false;
  }
}

function buildTable(rows) {
  const table = document.getElementById("result-table");
  table.innerHTML = "";

  // Header
  const thead = table.createTHead();
  const headerRow = thead.insertRow();
  Object.keys(rows[0]).forEach((key) => {
    const th = document.createElement("th");
    th.textContent = key;
    headerRow.appendChild(th);
  });

  // Body
  const tbody = table.createTBody();
  rows.forEach((row) => {
    const tr = tbody.insertRow();
    Object.values(row).forEach((val) => {
      const td = tr.insertCell();
      td.textContent = val !== null && val !== undefined ? val : "—";
    });
  });
}
