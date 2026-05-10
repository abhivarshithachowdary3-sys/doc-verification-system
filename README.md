# 🔐 Smart Document Verification System

> **Multi-agent AI pipeline for real-time identity document verification**
> OCR · LangGraph Agents · Fraud Detection · Blockchain Anchoring · FastAPI · Docker

---

## 🧠 Architecture Overview

```
Document Image
      │
      ▼
┌─────────────────────────────────────────────────────┐
│              LangGraph Orchestration                 │
│                                                     │
│  [OCR Agent] → [Classify] → [Extract] → [Fraud]    │
│                                   │           │     │
│                              (fraud?)   [External]  │
│                                   │           │     │
│                              [Report] ← [Blockchain]│
└─────────────────────────────────────────────────────┘
      │
      ▼
  JSON Report (status · fields · fraud flags · hash)
```

### Pipeline Stages

| Stage | Agent | What It Does |
|---|---|---|
| **1. OCR** | `ocr_agent.py` | 3-pass Tesseract extraction with preprocessing |
| **2. Classification** | `classification_agent.py` | Identifies doc type (Aadhaar/PAN/Passport/DL/VoterID) |
| **3. Extraction** | `extraction_agent.py` | Regex-based structured field extraction |
| **4. Fraud Detection** | `fraud_detection_agent.py` | Verhoeff checksum + 5 rule-based fraud checks |
| **5. External Verify** | `external_verification_agent.py` | UIDAI demographic auth (mock/live) |
| **6. Blockchain** | `blockchain/verifier.py` | SHA-256 hash anchoring on EVM chain |
| **7. Report** | `report_agent.py` | Final scored verdict + structured JSON |

---

## 🚀 Quick Start

### Option A — Local (Recommended for Dev)

```bash
# 1. Clone
git clone https://github.com/abhivarshithachowdary3-sys/doc-verification-system
cd doc-verification-system

# 2. Setup (creates venv, installs deps, creates .env)
chmod +x scripts/setup.sh && ./scripts/setup.sh

# 3. Configure (fill in your keys)
nano .env

# 4. Run
source .venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
```

Open: **http://localhost:8000** — Dashboard  
Open: **http://localhost:8000/docs** — Swagger API

### Option B — Docker

```bash
cd docker
docker compose up --build
```

Open: **http://localhost:80** — Dashboard  
Open: **http://localhost:8000/docs** — API

---

## 📡 API Reference

### `POST /api/v1/verify`
Submit a document image for full pipeline verification.

**Request** — `multipart/form-data`
```
file: <image file> (JPEG / PNG / WEBP / TIFF, max 10 MB)
```

**Response** — `200 OK`
```json
{
  "request_id": "uuid",
  "status": "verified",
  "verification_score": 0.87,
  "document_type": "aadhaar",
  "extracted_fields": {
    "aadhaar_number": "274990061497",
    "name": "Rahul Sharma",
    "dob": "15/08/1990",
    "gender": "MALE",
    "pincode": "500001"
  },
  "fraud_analysis": {
    "fraud_score": 0.0,
    "is_suspected": false,
    "flags": []
  },
  "external_verification": {
    "verified": true,
    "provider": "UIDAI_MOCK"
  },
  "blockchain": {
    "anchored": false,
    "document_hash": "a3f9c2...b41d",
    "tx_hash": "HASH_ONLY:a3f9c2..."
  },
  "ocr_confidence": 84.5,
  "processing_time_ms": 2341.7
}
```

### `GET /api/v1/verify/{request_id}`
Retrieve a previously submitted verification by ID.

### `GET /api/v1/health`
```json
{"status": "ok", "version": "1.0.0"}
```

### `GET /api/v1/status`
```json
{"tesseract_ocr": "ok", "langgraph": "ok", "web3": "ok"}
```

---

## 🧪 Testing

```bash
# Install test deps (included in requirements.txt)
source .venv/bin/activate

# Run all tests
pytest backend/tests/ -v

# Generate synthetic test images
python scripts/generate_synthetic_data.py

# Test with a real image via curl
curl -X POST http://localhost:8000/api/v1/verify \
  -F "file=@test_images/synthetic_aadhaar_1.png"
```

---

## ⛓️ Blockchain Setup (Optional)

The system runs in **hash-only mode** by default — all document hashes are computed and stored locally without on-chain writes.

To enable full blockchain anchoring:

```bash
# 1. Install Hardhat
npm install --save-dev hardhat

# 2. Start local chain
npx hardhat node

# 3. Deploy contract
python -m backend.blockchain.deployer

# 4. Add to .env
CONTRACT_ADDRESS=<deployed address>
DEPLOYER_PRIVATE_KEY=<account private key>
WEB3_PROVIDER_URL=http://localhost:8545
```

---

## 🔍 Fraud Detection Rules

| Rule | Severity | Description |
|---|---|---|
| `INVALID_AADHAAR_CHECKSUM` | Critical | Verhoeff algorithm fails on 12-digit UID |
| `FUTURE_DOB` | Critical | Date of birth is in the future |
| `IMPLAUSIBLE_DOB` | High | Age > 120 years |
| `LOW_OCR_CONFIDENCE` | High | < 40% confidence — possible printed fake |
| `BELOW_THRESHOLD_OCR` | Medium | < 60% confidence |
| `NAME_SPECIAL_CHARS` | Medium | Unexpected characters in name field |
| `NAME_TOO_SHORT` | Medium | Name ≤ 2 characters |
| `INVALID_PINCODE` | Low | Outside India's valid pincode range |

---

## 🗂️ Project Structure

```
doc-verification-system/
├── backend/
│   ├── agents/           # LangGraph agent nodes
│   ├── core/             # State, graph, config
│   ├── ocr/              # OCR engine + preprocessor
│   ├── blockchain/       # Web3, Solidity contract, deployer
│   ├── api/              # FastAPI routes + middleware
│   ├── database/         # SQLModel models + connection
│   └── tests/            # pytest test suite
├── frontend/             # Vanilla HTML/CSS/JS dashboard
├── ml_models/            # (Extendable) classifier + fraud model stubs
├── docker/               # Dockerfile + docker-compose
├── scripts/              # setup.sh + synthetic data generator
├── .env.example
├── .gitignore
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph 0.1.x |
| OCR | Tesseract 5.x + OpenCV + Pillow |
| API | FastAPI + Uvicorn |
| Database | SQLModel + SQLite (swap Postgres for prod) |
| Blockchain | Web3.py + Solidity 0.8.20 |
| Frontend | Vanilla HTML/CSS/JS |
| Containerization | Docker + Docker Compose |
| Testing | pytest + httpx |

---

## 📌 Roadmap

- [ ] PyTorch-based document classifier (CNN)
- [ ] LangGraph + GPT-4o for intelligent field extraction
- [ ] Redis + Celery async job queue
- [ ] Prometheus metrics endpoint
- [ ] Aadhaar OTP authentication (UIDAI live API)
- [ ] Mainnet/Polygon blockchain deployment

---

## 👤 Author

**Abhi Varshitha Chowdary Talluri**
B.Tech CSE — Vignan's LITS | AI/ML Research | Scopus-Indexed Author
GitHub: [abhivarshithachowdary3-sys](https://github.com/abhivarshithachowdary3-sys)

---

> Built as part of AI/ML research work. Not affiliated with UIDAI.
> Never process real Aadhaar data without proper authorization under the Aadhaar Act 2016.
