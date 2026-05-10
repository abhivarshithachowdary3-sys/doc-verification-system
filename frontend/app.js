const API_BASE = "http://localhost:8000/api/v1";

// ── DOM refs ─────────────────────────────────────────────────────────────────
const fileInput    = document.getElementById("fileInput");
const dropZone     = document.getElementById("dropZone");
const previewRow   = document.getElementById("previewRow");
const previewImg   = document.getElementById("previewImg");
const fileInfo     = document.getElementById("fileInfo");
const verifyBtn    = document.getElementById("verifyBtn");
const uploadCard   = document.getElementById("uploadCard");
const progressCard = document.getElementById("progressCard");
const resultCard   = document.getElementById("resultCard");
const apiStatus    = document.getElementById("apiStatus");
const resetBtn     = document.getElementById("resetBtn");

const STEPS = ["ocr","classify","extract","fraud","blockchain"];

let selectedFile = null;

// ── Health check ──────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`);
    if (r.ok) {
      apiStatus.textContent = "API Online";
      apiStatus.classList.add("ok");
    } else throw new Error();
  } catch {
    apiStatus.textContent = "API Offline";
  }
}
checkHealth();

// ── File handling ─────────────────────────────────────────────────────────────
function setFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  selectedFile = file;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  fileInfo.innerHTML = `<strong>${file.name}</strong><br>${(file.size/1024).toFixed(1)} KB · ${file.type}`;
  previewRow.style.display = "flex";
  verifyBtn.disabled = false;
}

fileInput.addEventListener("change", e => setFile(e.target.files[0]));
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  setFile(e.dataTransfer.files[0]);
});

// ── Pipeline progress simulation ──────────────────────────────────────────────
function animatePipeline() {
  return new Promise(resolve => {
    let i = 0;
    const id = setInterval(() => {
      if (i > 0) document.getElementById(`step-${STEPS[i-1]}`).classList.replace("active","done");
      if (i < STEPS.length) {
        document.getElementById(`step-${STEPS[i]}`).classList.add("active");
        i++;
      } else {
        clearInterval(id);
        resolve();
      }
    }, 600);
  });
}

function resetSteps() {
  STEPS.forEach(s => {
    const el = document.getElementById(`step-${s}`);
    el.classList.remove("active","done");
  });
}

// ── Verify ────────────────────────────────────────────────────────────────────
verifyBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  uploadCard.style.display = "none";
  progressCard.style.display = "block";
  resultCard.style.display = "none";
  resetSteps();

  const animPromise = animatePipeline();

  const formData = new FormData();
  formData.append("file", selectedFile);

  let data;
  try {
    const resp = await fetch(`${API_BASE}/verify`, { method: "POST", body: formData });
    data = await resp.json();
  } catch (e) {
    data = { status: "failed", errors: ["API connection failed — is the backend running?"] };
  }

  await animPromise;
  progressCard.style.display = "none";
  renderResult(data);
  resultCard.style.display = "block";
});

// ── Render result ─────────────────────────────────────────────────────────────
function renderResult(d) {
  const statusMap = {
    verified:        { cls: "verified", icon: "✅", label: "Document Verified" },
    fraud_suspected: { cls: "fraud",    icon: "🚨", label: "Fraud Suspected" },
    manual_review:   { cls: "manual",   icon: "⚠️",  label: "Manual Review Required" },
    failed:          { cls: "failed",   icon: "❌", label: "Verification Failed" },
  };
  const s = statusMap[d.status] || { cls: "failed", icon: "❓", label: d.status };

  document.getElementById("resultHeader").className = `result-header ${s.cls}`;
  document.getElementById("resultHeader").innerHTML =
    `<span>${s.icon}</span><span>${s.label}</span><span style="margin-left:auto;font-size:.85rem;font-weight:400">Score: ${((d.verification_score||0)*100).toFixed(0)}%</span>`;

  // Fields
  const fields = d.extracted_fields || {};
  const fl = document.getElementById("fieldsList");
  fl.innerHTML = Object.entries(fields).filter(([k]) => k !== "raw_text").map(([k,v]) =>
    v ? `<div class="field-row"><span class="field-key">${k.replace(/_/g," ")}</span><span class="field-val">${v}</span></div>` : ""
  ).join("") || "<p style='color:#94a3b8;font-size:.85rem'>No fields extracted</p>";

  // Fraud
  const fa = d.fraud_analysis || {};
  const flagsHtml = (fa.flags||[]).map(f =>
    `<div class="flag ${f.severity}">[${f.severity.toUpperCase()}] ${f.description}</div>`
  ).join("") || "<p style='color:#6b7280;font-size:.85rem'>No fraud flags detected ✓</p>";
  document.getElementById("fraudSection").innerHTML =
    `<div class="field-row"><span class="field-key">Fraud score</span><span class="field-val">${((fa.fraud_score||0)*100).toFixed(1)}%</span></div>
     <div style="margin-top:.75rem">${flagsHtml}</div>`;

  // Blockchain
  const bc = d.blockchain || {};
  document.getElementById("blockchainSection").innerHTML =
    `<div class="chain-info"><strong>Anchored</strong>${bc.anchored ? "Yes ✓" : "Hash-only mode"}</div>
     <div class="chain-info" style="margin-top:8px"><strong>Document hash</strong>${(bc.document_hash||"—").slice(0,20)}…</div>
     <div class="chain-info" style="margin-top:8px"><strong>TX hash</strong>${bc.tx_hash||"—"}</div>`;

  // Scores
  const scores = [
    ["OCR Confidence",       d.ocr_confidence || 0,         100],
    ["Verification Score",   (d.verification_score||0)*100, 100],
    ["Fraud Risk",           (fa.fraud_score||0)*100,       100],
  ];
  document.getElementById("scoresSection").innerHTML = scores.map(([label, val, max]) =>
    `<div class="score-bar-wrap">
       <div class="score-label"><span>${label}</span><span>${val.toFixed(1)}%</span></div>
       <div class="score-bar"><div class="score-fill" style="width:${Math.min(val,100)}%"></div></div>
     </div>`
  ).join("");
}

// ── Reset ─────────────────────────────────────────────────────────────────────
resetBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  previewRow.style.display = "none";
  verifyBtn.disabled = true;
  resultCard.style.display = "none";
  uploadCard.style.display = "block";
});
