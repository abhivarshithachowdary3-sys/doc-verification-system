#!/bin/bash
# ── Smart Document Verification System — Setup Script ────────────────────────
set -e
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Smart Document Verification System — Setup       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 1. Python version check
PY=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python version: $PY"

# 2. Virtual environment
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "✅ Virtual environment active"

# 3. Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
echo "✅ Dependencies installed"

# 4. Tesseract check
if command -v tesseract &>/dev/null; then
  echo "✅ Tesseract OCR found: $(tesseract --version 2>&1 | head -1)"
else
  echo "⚠️  Tesseract not found. Install it:"
  echo "   Ubuntu/Debian:  sudo apt-get install tesseract-ocr tesseract-ocr-hin"
  echo "   macOS:          brew install tesseract"
  echo "   Windows:        https://github.com/UB-Mannheim/tesseract/wiki"
fi

# 5. Environment file
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✅ .env file created from .env.example — please fill in your values"
else
  echo "✅ .env already exists"
fi

# 6. Create upload dir
mkdir -p uploads
echo "✅ uploads/ directory ready"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup complete! Start the server with:              ║"
echo "║                                                      ║"
echo "║  source .venv/bin/activate                           ║"
echo "║  uvicorn backend.api.main:app --reload               ║"
echo "║                                                      ║"
echo "║  API docs:  http://localhost:8000/docs               ║"
echo "║  Dashboard: http://localhost:8000                    ║"
echo "╚══════════════════════════════════════════════════════╝"
