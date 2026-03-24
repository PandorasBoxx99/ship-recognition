#!/usr/bin/env bash
# ============================================================
# Ship Recognition Platform — One-Click Install
# ============================================================
# Funktioniert unter Linux, macOS und Windows (WSL/Git Bash).
# Erstellt eine Python-venv, installiert Backend + Frontend,
# laedt das ML-Modell herunter und startet den Server.
#
# Aufruf:  bash install.sh
# ============================================================

set -euo pipefail

# ---- Windows: ensure essential tools are in PATH ----
# When bash.exe is invoked from PowerShell, PATH may be minimal.
for d in \
    "/c/Program Files/nodejs" \
    "/c/Program Files/Git/usr/bin" \
    "/c/Windows/System32" \
    "/c/Windows" \
    "/c/Program Files/Python311" \
    "/c/Program Files/Python312" \
    "$HOME/AppData/Local/Programs/Python/Python311" \
    "$HOME/AppData/Local/Programs/Python/Python312" \
    "$HOME/AppData/Local/Programs/Python/Python311/Scripts" \
    "$HOME/AppData/Local/Programs/Python/Python312/Scripts" \
    ; do
    [ -d "$d" ] && export PATH="$d:$PATH"
done

# ---- Konfiguration ----
VENV_DIR=".venv"
NODE_MIN="18"
PYTHON_MIN="3.11"
PORT="${PORT:-3025}"
USE_CPU="${USE_CPU:-1}"

# ---- Farben ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[FEHLER]${NC} $*"; exit 1; }

# ---- Voraussetzungen pruefen ----
info "Pruefe Voraussetzungen..."

# Python
PYTHON=""
for cmd in python3 python python.exe; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        if [ -n "$ver" ]; then
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            req_major=$(echo "$PYTHON_MIN" | cut -d. -f1)
            req_minor=$(echo "$PYTHON_MIN" | cut -d. -f2)
            if [ "$major" -gt "$req_major" ] 2>/dev/null || { [ "$major" -eq "$req_major" ] && [ "$minor" -ge "$req_minor" ]; } 2>/dev/null; then
                PYTHON="$cmd"
                break
            fi
        fi
    fi
done
[ -z "$PYTHON" ] && error "Python >= $PYTHON_MIN nicht gefunden. Bitte installieren: https://www.python.org/downloads/"
info "Python gefunden: $PYTHON ($($PYTHON --version 2>&1))"

# Node.js (fuer Frontend-Build)
# On Windows Git Bash, node/npm may not be in PATH — always add common locations
for np in "/c/Program Files/nodejs" "/c/Program Files (x86)/nodejs" "$APPDATA/nvm/current" "$HOME/AppData/Roaming/nvm/current"; do
    if [ -d "$np" ]; then
        export PATH="$np:$PATH"
    fi
done
if ! command -v node &>/dev/null; then
    warn "Node.js nicht gefunden. Frontend wird nicht gebaut."
    warn "Installiere Node.js >= $NODE_MIN: https://nodejs.org/"
    BUILD_FRONTEND=0
else
    NODE_VER=$(node -e "console.log(process.versions.node.split('.')[0])")
    if [ "$NODE_VER" -lt "$NODE_MIN" ]; then
        warn "Node.js $NODE_VER zu alt (min. $NODE_MIN). Frontend wird nicht gebaut."
        BUILD_FRONTEND=0
    else
        info "Node.js gefunden: $(node --version)"
        BUILD_FRONTEND=1
    fi
fi

# ---- venv erstellen ----
if [ ! -d "$VENV_DIR" ]; then
    info "Erstelle Python venv in $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    info "venv existiert bereits: $VENV_DIR"
fi

# venv aktivieren (save PATH first — venv activate can clobber it on Windows)
_SAVED_PATH="$PATH"
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
else
    error "Kann venv nicht aktivieren."
fi
# Restore essential paths that venv activation may have dropped
export PATH="$PATH:$_SAVED_PATH"
info "venv aktiviert: $(command -v python 2>/dev/null || echo 'python')"

# ---- pip aktualisieren ----
info "Aktualisiere pip..."
python -m pip install --upgrade pip --quiet

# ---- PyTorch installieren ----
if [ "$USE_CPU" = "1" ]; then
    info "Installiere PyTorch (CPU-only, ca. 200 MB)..."
    pip install --quiet \
        "torch>=2.0.0,<3.0.0" "torchvision>=0.15.0,<1.0.0" \
        --index-url https://download.pytorch.org/whl/cpu
else
    info "Installiere PyTorch (mit CUDA)..."
    pip install --quiet "torch>=2.0.0,<3.0.0" "torchvision>=0.15.0,<1.0.0"
fi

# ---- Python-Dependencies installieren ----
info "Installiere Python-Abhaengigkeiten..."
pip install --quiet -r requirements.txt

# ---- Projekt als Package installieren ----
info "Installiere Projekt als editierbares Package..."
pip install --quiet -e ".[dev,browser]"

# ---- Playwright Chromium installieren ----
info "Installiere Playwright Chromium (fuer Cloudflare-Bypass)..."
python -m playwright install chromium 2>/dev/null || warn "Playwright-Browser konnte nicht installiert werden. MarineTraffic-Scraping funktioniert evtl. nicht."

# ---- Frontend bauen ----
if [ "$BUILD_FRONTEND" = "1" ]; then
    info "Installiere Frontend-Abhaengigkeiten..."
    (cd frontend && npm ci --quiet 2>/dev/null || npm install --quiet)
    info "Baue Frontend..."
    (cd frontend && npm run build)
    info "Frontend gebaut: frontend-dist/"
else
    if [ -d "frontend-dist" ]; then
        info "Frontend-Build existiert bereits (frontend-dist/)"
    else
        warn "Kein Frontend-Build vorhanden. Starte 'cd frontend && npm install && npm run build' manuell."
    fi
fi

# ---- Verzeichnisse erstellen ----
info "Erstelle Datenverzeichnisse..."
mkdir -p downloads uploads augmented models/ship_classifier data logs

# ---- .env erstellen ----
if [ ! -f ".env" ]; then
    info "Erstelle .env aus .env.example..."
    cp .env.example .env
    # VPN standardmaessig deaktivieren
    sed -i 's/VPN_ENABLED=true/VPN_ENABLED=false/' .env 2>/dev/null || true
else
    info ".env existiert bereits"
fi

# ---- Datenbank migrieren ----
info "Fuehre Datenbank-Migrationen aus..."
python -m alembic upgrade head 2>/dev/null || warn "Alembic-Migration fehlgeschlagen (evtl. schon aktuell)"

# ---- ML-Modell herunterladen ----
if [ ! -f "models/ship_classifier/config.json" ]; then
    info "Lade ML-Modell herunter (ViT Ship Classifier)..."
    python -c "
from transformers import ViTForImageClassification, ViTImageProcessor
name = 'dima806/10_ship_types_image_detection'
print('Downloading ViT ship classifier...')
p = ViTImageProcessor.from_pretrained(name)
m = ViTForImageClassification.from_pretrained(name)
p.save_pretrained('models/ship_classifier')
m.save_pretrained('models/ship_classifier')
print('Model saved.')
"
else
    info "ML-Modell bereits vorhanden"
fi

# ---- Fertig ----
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN} Installation abgeschlossen! Server startet jetzt...${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  ${GREEN}>>> Browser oeffnen: http://localhost:$PORT <<<${NC}"
echo ""
echo -e "  API-Docs:  http://localhost:$PORT/docs"
echo ""
echo -e "${YELLOW}──────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW} Naechstes Mal manuell starten:${NC}"
echo ""
echo "  Linux / macOS / Git Bash:"
echo "    cd $(pwd)"
echo "    source $VENV_DIR/bin/activate"
echo "    python run.py"
echo ""
echo "  Windows PowerShell:"
echo "    cd $(pwd)"
echo "    .\\.venv\\Scripts\\activate"
echo "    python run.py"
echo ""
echo -e "${YELLOW} Server stoppen:${NC}"
echo "    Strg+C (im Terminal wo der Server laeuft)"
echo ""
echo -e "${YELLOW} venv deaktivieren:${NC}"
echo "    deactivate"
echo -e "${YELLOW}──────────────────────────────────────────────────────────${NC}"
echo ""

# ---- Server starten ----
info "Starte Server auf http://localhost:$PORT ..."
info "Stoppen mit Strg+C"
echo ""
python run.py
