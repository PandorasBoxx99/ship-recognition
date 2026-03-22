#!/bin/bash
# ============================================================
# Ship Recognition Platform - Setup Script
# ============================================================

set -e

echo "========================================"
echo "  Ship Recognition Platform - Setup"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ---- Check Python ----
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Python nicht gefunden! Bitte Python 3.11+ installieren.${NC}"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}Python gefunden:${NC} $PY_VERSION"

# ---- Check Node.js ----
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo -e "${GREEN}Node.js gefunden:${NC} $NODE_VERSION"
else
    echo -e "${YELLOW}Node.js nicht gefunden. Frontend-Build wird uebersprungen.${NC}"
    echo -e "${YELLOW}Installiere Node.js 20+ fuer das Frontend: https://nodejs.org${NC}"
fi

# ---- Create virtual environment ----
if [ ! -d "venv" ]; then
    echo -e "\n${YELLOW}Erstelle virtuelle Umgebung...${NC}"
    $PYTHON -m venv venv
fi

# Activate venv
echo -e "${YELLOW}Aktiviere virtuelle Umgebung...${NC}"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# ---- Install Python dependencies ----
echo -e "\n${YELLOW}Installiere Python-Abhaengigkeiten...${NC}"
pip install --upgrade pip -q
pip install -e ".[dev]" -q
echo -e "${GREEN}Python-Pakete installiert.${NC}"

# ---- Create directories ----
echo -e "\n${YELLOW}Erstelle Verzeichnisse...${NC}"
mkdir -p downloads uploads augmented models/ship_classifier data logs

# ---- Create .env if not exists ----
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Erstelle .env aus .env.example...${NC}"
    cp .env.example .env
fi

# ---- Initialize / migrate database ----
echo -e "\n${YELLOW}Initialisiere Datenbank...${NC}"
if [ -f "schiffs-scraper.db" ]; then
    echo "Vorhandene Datenbank gefunden. Fuehre Migration aus..."
    $PYTHON scripts/migrate_v1.py 2>/dev/null || true
fi
$PYTHON -m alembic upgrade head 2>/dev/null || $PYTHON -c "
from backend.database import Base, engine, init_db
import backend.models
init_db()
print('Datenbank erstellt.')
"

# ---- Build Frontend ----
if command -v node &> /dev/null; then
    echo -e "\n${YELLOW}Installiere Frontend-Abhaengigkeiten...${NC}"
    cd frontend
    npm ci -q 2>/dev/null || npm install -q
    echo -e "${YELLOW}Baue Frontend...${NC}"
    npm run build
    cd ..
    echo -e "${GREEN}Frontend gebaut.${NC}"
else
    echo -e "\n${YELLOW}Frontend-Build uebersprungen (Node.js nicht installiert).${NC}"
fi

# ---- Download ML model ----
if [ ! -f "models/ship_classifier/model.safetensors" ]; then
    echo -e "\n${YELLOW}Lade ML-Modell herunter (~350 MB)...${NC}"
    $PYTHON -c "
from transformers import ViTForImageClassification, ViTImageProcessor

model_dir = 'models/ship_classifier'
model_name = 'dima806/10_ship_types_image_detection'

print('Downloading model from HuggingFace...')
processor = ViTImageProcessor.from_pretrained(model_name)
model = ViTForImageClassification.from_pretrained(model_name)

processor.save_pretrained(model_dir)
model.save_pretrained(model_dir)
print('Modell gespeichert.')
" || echo -e "${YELLOW}Modell-Download uebersprungen (wird beim ersten Start geladen).${NC}"
fi

echo ""
echo -e "${GREEN}========================================"
echo "  Setup abgeschlossen!"
echo "========================================"
echo ""
echo "  Starten mit:"
echo "    source venv/bin/activate"
echo "    python run.py"
echo ""
echo "  Dann oeffnen: http://localhost:3025"
echo "  API-Docs:     http://localhost:3025/docs"
echo -e "========================================${NC}"
