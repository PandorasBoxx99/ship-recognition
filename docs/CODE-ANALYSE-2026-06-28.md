# Code-Analyse — Ship Recognition Platform

**Datum:** 2026-06-28
**Umfang:** ~8.000 Zeilen Python-Backend (FastAPI) + ~3.000 Zeilen Frontend (React 19/TS)
**Methode:** Vollständige Durchsicht von Backend (Services, Router, ORM), ML-Engine, Frontend, Tests, Build/CI. Kernbefunde stichprobenartig per `grep` verifiziert.

---

## Gesamteindruck

Funktional weit fortgeschritten (~70–80 % nutzbar), sauber geschichtete Architektur
(Router → Service → ML-Engine/ORM). Hauptproblem: Das Projekt trägt **zwei „Eras"
parallel** mit sich (v1 Flask/Legacy + v2 FastAPI/normalisiert) — die Hauptquelle für
Verwirrung und Daten-Inkonsistenz. Systematische Lücken bei **Thread-Safety,
Input-Validierung und Daten-Konsistenz**, die in Produktion beißen würden.

---

## 🔴 Kritische Befunde

### 1. Keine Thread-Safety bei geteiltem Status (durchgängig)
`grep` bestätigt: **kein einziges `threading.Lock` im gesamten Code.** Gleichzeitig
laufen ≥4 Hintergrund-Worker mit globalen Status-Dicts, die parallel gelesen/geschrieben
werden:
- `ml_engine.py:24-25` — `_training_status`, `_augment_status`
- `classify.py:95` — `_batch_status`
- `detection_service.py:26` — `_detection_status`
- `scrape_service.py:62` — `active_jobs`

Konkret:
- **TOCTOU-Race** (`ml_engine.py:237`, `:352`): `if status['running']: return` gefolgt von
  `thread.start()` ohne Lock → zwei gleichzeitige Requests starten zwei Trainings.
- **Modell-Laden ohne Lock** (`detection_service.py:29`, `ml_engine.py:45`): zwei parallele
  Requests laden das Modell doppelt in den Speicher (~350–400 MB pro ViT).

### 2. Upload ohne Größen-/Typ-Limit (DoS)
`classify.py:34` — `image_data = await image.read()` liest unbegrenzt in den RAM und
schreibt direkt auf Platte. Kein Size-Check, keine MIME-Validierung. `MAX_UPLOAD_SIZE_MB=25`
existiert in `config.py:62`, **wird aber nirgends durchgesetzt.**

### 3. ~930 Zeilen toter Legacy-Code
- **`app.py` (822 Zeilen)** — altes Flask-Monolith. Flask ist **nicht** in den Dependencies
  (verifiziert) → nicht ausführbar. Kein Launcher startet es; einzige Erwähnung ist ein
  Kommentar (`scrape_service.py:61`). **Endpunkt-Abgleich: alle 29 Flask-Routen sind in
  FastAPI portiert (29/29), FastAPI ist strikte Obermenge** → kein Referenzwert mehr.
- **`schema.sql` (108 Zeilen)** — nur v1-Tabellen, einziger Laufzeit-Konsument war `app.py:42`.
  FastAPI erstellt Tabellen über `Base.metadata.create_all` + Alembic. Wird sinnlos ins
  Docker-Image kopiert (`Dockerfile:43`).

→ Empfehlung: beide entfernen (git bewahrt sie auf). Verifiziert: v2-Portierung vollständig.

### 4. v1/v2 Daten-Inkonsistenz
Zwei parallele Datenmodelle/APIs, **nicht synchron gehalten**:
- `/api/ships` (`ships.py`) liest v1-Tabelle `items`
- `/api/v2/ships` (`ship_entities.py`) liest v2-Tabelle `ships`
- `stats.py` zählt **nur v1** → Dashboard-Zahlen können von der v2-Schiffsliste abweichen.

v1→v2-Migration (`002_normalize_schema.py:207`) nutzt `LEFT JOIN ... WHERE status='downloaded'`
→ Bilder ohne gematchtes Schiff verlieren `ship_id`; `crop_rank`/`parent_image_id` bleiben leer.
**Migration durch keinen Test abgedeckt.**

### 5. Speicher-Leaks im ML-Pfad
- `ml_engine.py:121` — `Image.open(...)` ohne Context-Manager/`.close()` (auch `:298`, `:395`).
- Nach (fehlgeschlagenem) Training wird ein zweites Modell geladen, das alte nie freigegeben
  → doppelter RAM-Verbrauch.

---

## 🟠 Hohe Priorität

| Befund | Ort | Problem |
|---|---|---|
| Settings nicht persistent | `SettingsPage.tsx:232-250, 286-304` | Eingabefelder ohne Save-Handler — Eingaben gehen verloren |
| Blocking-Call in async-Route | `classify.py:26+43` | `async def` ruft synchrones `classify_image()` → blockiert Event-Loop. Fix: `await asyncio.to_thread(...)` |
| 6 API-Calls umgehen den Client | ClassifyPage, SettingsPage, ScraperPage, ExtraktorPage, DokuPage | Direkte `axios`-Calls statt `api/client.ts` → keine zentrale Fehlerbehandlung/Typsicherheit |
| Silent Failures | `ml_engine.py:296-314` | Defekte Bilder bei Augmentation nur geprintet; Status meldet „Done" trotz halber Ausbeute |
| Keine Job-Timeouts | scrape/detection/classify-Worker | Hängender `page.goto()`/`trainer.train()` blockiert Thread unbegrenzt, kein Watchdog |
| Frontend Memory-Leak | `ExtraktorPage.tsx:23-35` | `setInterval`-Cleanup bei Unmount/Error unsicher |

---

## 🟡 Mittlere Priorität

- **Test-Qualität:** 11 Dateien / ~57 Tests, überwiegend Smoke-Tests (`assert status==200`).
  ML und VPN weggemockt; `ml_engine.py` und v1→v2-Migration **komplett ungetestet**.
- **CI-Lücken:** CI läuft `ruff` + `pytest` (`ci.yml:30`), aber ohne Coverage, ohne
  Migrations-Test, ohne Security-Scan. *Hinweis: CLAUDE.md behauptet „CI runs only ruff" —
  veraltet, pytest läuft tatsächlich.*
- **Dependency-Drift:** `requirements.txt` ↔ `pyproject.toml` inkonsistent (`pytest-asyncio`,
  `ruff` fehlen in requirements; `httpx` falsch platziert). Nur `>=`-Pins.
- **Datenmodell:** `ship.py:49-53` hängt FK nachträglich per `append_constraint` an
  (Antipattern); `image.py:26` nutzt `Integer` für `is_synthetic` statt `Boolean`.
- **Path-Traversal-Risiko:** `advanced.py:46` nutzt `image_path`-Parameter direkt in
  `os.path.exists()` ohne Prüfung gegen `BASE_DIR`.
- **VPN-Service „Logging-only":** `connect/disconnect` schreiben nur DB-Einträge; „Connected"
  heißt nur „API-Token gültig", keine echte Systemverbindung.
- **Hardcoded-Werte (Frontend):** Länderlisten, Farben, Version „2.0.0"
  (`SettingsPage.tsx:163,328`) statt vom Backend.

---

## ML-Engine: Training echt oder Stub?

**Echtes Fine-Tuning** (HuggingFace `Trainer`, Custom-Labels, Train/Val-Split, Best-Checkpoint),
aber **produktions-unreif:** zu kleine Batch-Size, keine Gradient-Accumulation, kein fp16,
keine Augmentation in der Pipeline, Minimum von 10 Bildern unrealistisch (sollte 50–100+ sein),
kein LR-Warmup, nicht seeded (nicht reproduzierbar).

---

## Empfohlene Reihenfolge

**Sofort (Aufräumen, risikolos):**
1. `app.py` + `schema.sql` löschen (Portierung verifiziert vollständig)
2. `requirements.txt`/`pyproject.toml` synchronisieren
3. CLAUDE.md CI-Abschnitt korrigieren

**Kurzfristig (Robustheit):**
4. `threading.Lock` für alle Status-Dicts + atomares check-and-set
5. Upload-Limit + MIME-Check in `classify.py` (`MAX_UPLOAD_SIZE_MB` nutzen)
6. SettingsPage Save-Handler ergänzen
7. Blocking-Calls in async-Routen → `asyncio.to_thread`

**Mittelfristig (Konsistenz & Qualität):**
8. v1→v2-Migration mit Test absichern; v1-API deprecaten?
9. `stats.py` auf konsistente Datenquelle umstellen
10. Echte Assertions + Migrations-/ML-Tests; Coverage in CI
