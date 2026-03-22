#!/bin/bash
# ============================================================
# Ship-Scraper - One-Click Setup
# ============================================================

set -e

echo "========================================"
echo "  Ship-Scraper Setup"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Python nicht gefunden! Bitte Python 3.8+ installieren.${NC}"
    exit 1
fi

echo -e "${GREEN}Python gefunden:${NC} $($PYTHON --version)"

# Create virtual environment
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

# Install dependencies
echo -e "\n${YELLOW}Installiere Abhaengigkeiten...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
echo -e "\n${YELLOW}Erstelle Verzeichnisse...${NC}"
mkdir -p downloads uploads augmented models/ship_classifier

# Initialize database
echo -e "\n${YELLOW}Initialisiere Datenbank...${NC}"
$PYTHON -c "
import sqlite3, os
with open('schema.sql', 'r') as f:
    schema = f.read()
conn = sqlite3.connect('schiffs-scraper.db')
conn.executescript(schema)
conn.commit()
conn.close()
print('Datenbank erstellt.')
"

# Check if model exists
if [ ! -f "models/ship_classifier/model.safetensors" ]; then
    echo -e "\n${YELLOW}Lade ML-Modell herunter...${NC}"
    $PYTHON -c "
from transformers import ViTForImageClassification, ViTImageProcessor
import os

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
echo "    python app.py"
echo ""
echo "  Dann oeffnen: http://localhost:3025"
echo -e "========================================${NC}"
