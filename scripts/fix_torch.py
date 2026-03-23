#!/usr/bin/env python3
"""
Fix broken torch installation.

Detects Anaconda (DLL conflicts) and creates a clean venv with CPU-only torch.

Usage:
    python scripts/fix_torch.py
"""

import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_anaconda():
    return "anaconda" in sys.prefix.lower() or "conda" in sys.prefix.lower()


def venv_python():
    if sys.platform == "win32":
        return os.path.join(BASE, "venv", "Scripts", "python.exe")
    return os.path.join(BASE, "venv", "bin", "python")


def main():
    print("=== Ship Recognition - Torch Fix ===\n")
    print(f"Python:   {sys.executable}")
    print(f"Anaconda: {'JA (DLL-Konflikte moeglich)' if is_anaconda() else 'Nein'}\n")

    if is_anaconda():
        print("Anaconda erkannt — erstelle saubere venv mit CPU-only torch.\n")

        # Create venv
        venv_dir = os.path.join(BASE, "venv")
        if not os.path.exists(venv_dir):
            print("1. Erstelle venv...")
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        else:
            print("1. venv existiert bereits")

        py = venv_python()

        # Upgrade pip
        subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip", "-q"], capture_output=True)

        # Install CPU torch
        print("2. Installiere torch (CPU-only) in venv...")
        subprocess.run([
            py, "-m", "pip", "install",
            "torch", "torchvision",
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ], check=True)

        # Install project
        print("3. Installiere Projekt in venv...")
        subprocess.run([py, "-m", "pip", "install", "-e", f"{BASE}[dev]"], check=True)

    else:
        py = sys.executable
        print("Reinstalliere torch (CPU-only)...")
        subprocess.run([py, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
                       capture_output=True)
        subprocess.run([
            py, "-m", "pip", "install",
            "torch", "torchvision",
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ], check=True)

    # Verify
    print("\n4. Verifiziere...")
    result = subprocess.run([
        py if not is_anaconda() else venv_python(), "-c",
        "import torch; print(f'  torch {torch.__version__} OK'); "
        "t = torch.zeros(1); print(f'  Tensor OK'); "
        "from transformers import ViTForImageClassification; print('  transformers OK')"
    ], capture_output=True, text=True)
    print(result.stdout)

    if result.returncode != 0:
        print(f"FEHLER: {result.stderr}")
        return

    print("=== ERFOLGREICH! ===\n")
    if is_anaconda():
        if sys.platform == "win32":
            print("Starte den Server so:")
            print("  venv\\Scripts\\activate")
            print("  python run.py")
        else:
            print("Starte den Server so:")
            print("  source venv/bin/activate")
            print("  python run.py")
    else:
        print("Starte den Server: python run.py")


if __name__ == "__main__":
    main()
