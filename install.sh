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
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[FEHLER]${NC} $*"; exit 1; }

# ---- Spinner fuer lange Operationen ----
spinner() {
    local pid=$1
    local msg="${2:-Bitte warten...}"
    local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  ${CYAN}${frames[$i]}${NC} %s " "$msg"
        i=$(( (i + 1) % ${#frames[@]} ))
        sleep 0.1
    done
    wait "$pid"
    local exit_code=$?
    printf "\r  ${GREEN}✓${NC} %s \n" "$msg"
    return $exit_code
}

# Fuehrt einen Befehl mit Spinner aus
run_with_spinner() {
    local msg="$1"
    shift
    "$@" &>/dev/null &
    spinner $! "$msg"
}

# ---- Voraussetzungen pruefen ----
echo ""
echo -e "${BOLD}🚢 Ship Recognition Platform — Installer${NC}"
echo ""
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
echo -e "  ${GREEN}✓${NC} Python: $($PYTHON --version 2>&1)"

# Node.js (fuer Frontend-Build)
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
        echo -e "  ${GREEN}✓${NC} Node.js: $(node --version)"
        BUILD_FRONTEND=1
    fi
fi

# ---- venv erstellen ----
echo ""
if [ ! -d "$VENV_DIR" ]; then
    run_with_spinner "Python venv erstellen" "$PYTHON" -m venv "$VENV_DIR"
else
    echo -e "  ${GREEN}✓${NC} venv existiert bereits"
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

# ---- pip aktualisieren ----
run_with_spinner "pip aktualisieren" python -m pip install --upgrade pip --quiet

# ---- PyTorch installieren ----
if [ "$USE_CPU" = "1" ]; then
    run_with_spinner "PyTorch installieren (CPU, ~200 MB)" pip install --quiet \
        "torch>=2.0.0,<3.0.0" "torchvision>=0.15.0,<1.0.0" \
        --index-url https://download.pytorch.org/whl/cpu
else
    run_with_spinner "PyTorch installieren (CUDA)" pip install --quiet \
        "torch>=2.0.0,<3.0.0" "torchvision>=0.15.0,<1.0.0"
fi

# ---- Python-Dependencies installieren ----
run_with_spinner "Python-Abhaengigkeiten installieren" pip install --quiet -r requirements.txt

# ---- Projekt als Package installieren ----
run_with_spinner "Projekt installieren" pip install --quiet -e ".[dev,browser]"

# ---- Playwright Chromium installieren ----
python -m playwright install chromium &>/dev/null &
spinner $! "Playwright Chromium installieren" || warn "Playwright fehlgeschlagen — MarineTraffic-Scraping evtl. nicht moeglich"

# ---- Frontend bauen ----
if [ "$BUILD_FRONTEND" = "1" ]; then
    (cd frontend && npm ci --quiet 2>/dev/null || npm install --quiet) &>/dev/null &
    spinner $! "Frontend-Abhaengigkeiten installieren"
    (cd frontend && npm run build) &>/dev/null &
    spinner $! "Frontend bauen"
else
    if [ -d "frontend-dist" ]; then
        echo -e "  ${GREEN}✓${NC} Frontend-Build existiert bereits"
    else
        warn "Kein Frontend-Build. Manuell: cd frontend && npm install && npm run build"
    fi
fi

# ---- Verzeichnisse erstellen ----
mkdir -p downloads uploads augmented models/ship_classifier data logs

# ---- .env erstellen ----
if [ ! -f ".env" ]; then
    cp .env.example .env
    sed -i 's/VPN_ENABLED=true/VPN_ENABLED=false/' .env 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} .env erstellt"
else
    echo -e "  ${GREEN}✓${NC} .env existiert bereits"
fi

# ---- Datenbank migrieren ----
run_with_spinner "Datenbank migrieren" python -m alembic upgrade head 2>/dev/null || true

# ---- ML-Modell herunterladen ----
if [ ! -f "models/ship_classifier/config.json" ]; then
    python -c "
from transformers import ViTForImageClassification, ViTImageProcessor
name = 'dima806/10_ship_types_image_detection'
p = ViTImageProcessor.from_pretrained(name)
m = ViTForImageClassification.from_pretrained(name)
p.save_pretrained('models/ship_classifier')
m.save_pretrained('models/ship_classifier')
" &>/dev/null &
    spinner $! "ML-Modell herunterladen (ViT Ship Classifier)"
else
    echo -e "  ${GREEN}✓${NC} ML-Modell bereits vorhanden"
fi

# ---- Freien Port finden ----
find_free_port() {
    local port=$1
    while python -c "import socket; s=socket.socket(); s.settimeout(0.5); exit(0 if s.connect_ex(('127.0.0.1',$port))==0 else 1)" 2>/dev/null; do
        warn "Port $port ist belegt"
        port=$((port + 1))
    done
    echo "$port"
}

PORT=$(find_free_port "$PORT")

# ---- Fertig ----
PROJ_DIR=$(pwd)
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Installation abgeschlossen!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  ${BOLD}${GREEN}>>> http://localhost:$PORT <<<${NC}"
echo ""
echo -e "  API-Docs:  http://localhost:$PORT/docs"
echo ""
echo -e "${YELLOW}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${YELLOW}│${NC} ${BOLD}Server stoppen:${NC}                                         ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   Strg+C                                                ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}                                                          ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC} ${BOLD}Naechstes Mal starten (Windows PowerShell):${NC}              ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   cd ${PROJ_DIR}  ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   .\\.venv\\Scripts\\activate                               ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   python run.py                                          ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}                                                          ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC} ${BOLD}Naechstes Mal starten (Linux/macOS/Git Bash):${NC}            ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   cd ${PROJ_DIR}  ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   source .venv/bin/activate                              ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   python run.py                                          ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}                                                          ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC} ${BOLD}venv beenden:${NC}                                            ${YELLOW}│${NC}"
echo -e "${YELLOW}│${NC}   deactivate                                             ${YELLOW}│${NC}"
echo -e "${YELLOW}└──────────────────────────────────────────────────────────┘${NC}"
echo ""

# ---- Server starten ----
info "Starte Server auf http://localhost:$PORT ..."
info "Stoppen mit Strg+C"
echo ""
PORT=$PORT python -c "
import uvicorn, os
port = int(os.environ.get('PORT', 3025))
uvicorn.run('backend.main:app', host='0.0.0.0', port=port)
"
