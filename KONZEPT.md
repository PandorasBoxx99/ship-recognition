# Schiffs-Bilderkennung — Konzept & Recherche

**Projekt für:** Ronny (via Bernhard)
**Erstellt:** 2026-02-04
**Status:** Konzeptphase

---

## 1. ML-Modelle für Schiffserkennung

### 1.1 Vortrainierte Modelle (Ready-to-Use)

| Modell | Typ | Genauigkeit | CPU-tauglich | Link |
|--------|-----|-------------|--------------|------|
| **dima806/10_ship_types_image_detection** | Image Classification (ViT) | **99.6%** | ✅ Ja | [HuggingFace](https://huggingface.co/dima806/10_ship_types_image_detection) |
| **dima806/vessel_ship_types_image_detection** | Image Classification | ~99% | ✅ Ja | [HuggingFace](https://huggingface.co/dima806/vessel_ship_types_image_detection) |
| **nielsr/yolov5-ship-detection** | Object Detection | Gut | ✅ Ja | [HuggingFace](https://huggingface.co/nielsr/yolov5-ship-detection) |
| **YOLO26n (Ultralytics)** | Object Detection | 40.9 mAP | ✅ 39ms CPU | [GitHub](https://github.com/ultralytics/ultralytics) |

### 1.2 Erkannte Schiffstypen (dima806 Modell)

Das beste vortrainierte Modell erkennt **10 Schiffstypen**:
- Bulkers (Massengutfrachter)
- Container Ship
- Cruise (Kreuzfahrtschiffe)
- Tug (Schlepper)
- Sailboat (Segelboote)
- Recreational (Freizeitboote)
- Car Carrier (Autotransporter)
- DDG (Zerstörer)
- Aircraft Carrier (Flugzeugträger)
- Submarine (U-Boote)

### 1.3 Empfehlung: Custom Fine-Tuning

Für Ronny's spezifische Anforderungen (z.B. Binnenschiffe, spezielle Typen):
1. **Basis:** YOLO26n oder ViT (Vision Transformer)
2. **Fine-Tuning** auf eigene Bilder (~500-1000 pro Kategorie)
3. **Hardware:** Normaler PC mit 8GB RAM reicht für Inference

---

## 2. Architektur-Optionen

### Option A: Web App ⭐ EMPFOHLEN

**Vorteile:**
- ✅ Plattformunabhängig (Windows, Mac, Linux)
- ✅ Keine Installation nötig
- ✅ Einfach zu deployen (auch lokal)
- ✅ Für Bernhard zum Testen ideal

**Nachteile:**
- ❌ Braucht Server/lokalen Start

**Tech-Stack:**
- Flask/FastAPI Backend
- ONNX Runtime für ML-Inference
- Vanilla JS Frontend

### Option B: Browser-Extension

**Vorteile:**
- ✅ Direkt in ShipSpotting etc. nutzbar
- ✅ Kein separates Fenster

**Nachteile:**
- ❌ Komplexere Entwicklung
- ❌ Browser-spezifisch (Chrome, Firefox separat)
- ❌ Updates schwieriger

### Option C: Desktop-App (Electron/Tauri)

**Vorteile:**
- ✅ Native Erfahrung
- ✅ Offline-fähig

**Nachteile:**
- ❌ Größerer Entwicklungsaufwand
- ❌ Separate Builds für Windows/Mac/Linux

### 🎯 Empfehlung

**Phase 1:** Web App (Flask) — schnell, flexibel, testbar
**Phase 2:** Falls gewünscht, Browser-Extension für Integration

---

## 3. Datenquellen für Schiffsbilder

### 3.1 Primäre Quellen

| Quelle | URL | Bilder | Schutz |
|--------|-----|--------|--------|
| **ShipSpotting** | shipspotting.com | ~2 Mio | Cloudflare ⚠️ |
| **MarineTraffic** | marinetraffic.com/photos | ~3 Mio | Cloudflare ⚠️ |
| **VesselFinder** | vesselfinder.com | ~500k | Moderat |
| **FleetMon** | fleetmon.com | ~200k | API verfügbar |

### 3.2 Scraping-Strategie

**Problem:** Große Seiten haben Bot-Protection

**Lösung:**
1. **VPN** vor jedem Scraping-Session (IP-Rotation)
2. **Langsame Requests** (1-5 Sek Delay, randomisiert)
3. **User-Agent Rotation**
4. **Session/Cookie-Handling**
5. **Respektieren von robots.txt** (soweit möglich)

### 3.3 Rechtliche Aspekte

⚠️ **Wichtig für Ronny zu wissen:**

- Bilder auf ShipSpotting/MarineTraffic haben **Urheberrecht** (Fotografen)
- Für **privaten/Forschungszweck** oft geduldet
- Für **kommerzielle Nutzung** → Lizenzen einholen!
- **Alternative:** Kaggle Datasets (bereits lizenziert für ML)

**Empfohlene Datasets:**
- [Ship Image Classification Dataset](https://www.kaggle.com/datasets/dima806/game-of-deep-learning-ship-datasets) (10k+ Bilder)
- [HRSC2016](http://www.escience.cn/people/liuzikun/index.html) (Satellite Ship Detection)

---

## 4. Prototyp: Schiffs-Daten-Scraper

### 4.1 Features (MVP)

1. ✅ URL eingeben (z.B. ShipSpotting Kategorie)
2. ✅ Ordnerstruktur/Kategorien anzeigen
3. ✅ Auswahl per Checkbox
4. ✅ Limit setzen (erste N Bilder)
5. ✅ VPN-Verbindung prüfen/aktivieren
6. ✅ Download mit Rate-Limiting
7. ✅ Fortschrittsanzeige
8. ✅ SQLite-Speicherung (Metadaten)

### 4.2 Tech-Stack

- **Backend:** Flask + requests + BeautifulSoup
- **Frontend:** Vanilla JS (wie andere WebApps)
- **Datenbank:** SQLite
- **VPN:** NordVPN CLI Integration
- **Port:** 3025

### 4.3 Pfad

```
/root/Sync/Projekte/05-WebApps/schiffs-scraper/
```

---

## 5. Nächste Schritte

1. ✅ Konzept-Dokument erstellt
2. 🔄 Prototyp-WebApp entwickeln
3. ⏳ Test mit ShipSpotting/VesselFinder
4. ⏳ ML-Modell Integration (Phase 2)

---

## Anhang: Ressourcen

- NordVPN Skill: `/root/clawd/skills/nordvpn/SKILL.md`
- YOLO Docs: https://docs.ultralytics.com/
- HuggingFace Ship Models: https://huggingface.co/models?search=ship+detection
