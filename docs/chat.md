# Chat-Protokoll — Ship Recognition (Sitzung 2026-06-28)

Vollständiges, chronologisches Protokoll der Arbeitssitzung. Kein wörtliches
Transkript, sondern jede Anfrage des Nutzers + was umgesetzt wurde + Commits.
Inhaltliche Details siehe `docs/CODE-ANALYSE-2026-06-28.md` und die Memory-Notizen.

---

## 1. Komplette Code-Analyse
**Anfrage:** „analysiere den kompletten Code im Ordner ship-recognition".
- Vier parallele Explore-Agenten (Backend, ML-Engine, Frontend, Tests/Config).
- Ergebnis: **5 kritische Befunde** — (1) keine Thread-Safety, (2) Upload ohne
  Limit, (3) ~930 Z. toter Code (`app.py`/`schema.sql`), (4) v1/v2-Inkonsistenz,
  (5) ML-Speicher-Leaks. Dokumentiert in `docs/CODE-ANALYSE-2026-06-28.md`.

## 2. Toter Code verifiziert
**Anfrage:** „warum willst du app.py und schema.sql löschen?" → Beweislage gezeigt.
**Anfrage:** „mach den Endpunkt-Abgleich" → **29/29 Flask-Routen** sind in FastAPI
portiert; FastAPI ist strikte Obermenge → Löschen ist sicher.

## 3. Visuelle Versionshistorie (Git)
**Anfrage:** „wie kann ich auf eine ältere Version zugreifen / visuelle Historie".
- VS-Code-Extension **Git Graph** installiert, `.vscode/extensions.json` angelegt.
- Wiederherstellungspunkt-Tag `stand-2026-06-28` gesetzt; Bedienung erklärt
  (Checkout/Create Branch ungefährlich, Reset gefährlich).
- Git-Identität gesetzt: **Ronny Ruben / RONNY.RUBEN@gmx.de**.

## 4. GitHub-Konto umgestellt
**Anfrage:** „teste Zugriff auf meinen GitHub-Account, auch schreibend".
- Festgestellt: Remote zeigte auf **fremdes Konto `BurnHardCoding`**.
- **Anfrage:** Username `PandorasBoxx99` → Remote umgestellt, altes Token aus dem
  Git Credential Manager entfernt, als PandorasBoxx99 neu authentifiziert.
- `master` + `develop` + Tags ins eigene Repo gepusht.
- **Anfrage:** „Meilensteine" → 6 beschriftete Tags `m0…m5` gesetzt + gepusht.
- Repo: https://github.com/PandorasBoxx99/ship-recognition

## 5. Doku gespeichert
**Anfrage:** „speicher Chatverlauf und Analyse" → `docs/CODE-ANALYSE-2026-06-28.md`
und `docs/SESSION-LOG-2026-06-28.md` angelegt und committet.

## 6. CI repariert
**Anfrage:** „GitHub-Mail: Backend Lint und Backend Tests failed" (erster CI-Lauf).
- **Tests:** 11 veraltete VPN-Tests (mockten altes CLI/`subprocess`) auf die
  REST-API umgeschrieben; deutsche Fehlertexte angepasst.
- **Lint:** 104 ruff-Verstöße behoben (Imports, lange Zeilen, `# noqa: E402` nur
  für bewusste Router-Imports).

## 7. NordVPN-Analyse
**Anfrage:** „analysiere die NordVPN-Integration".
- Befund: **keine CLI** (entfernt), nutzt die **REST-API** mit Access Token; der
  **Scraper-Traffic wurde aber NICHT getunnelt** (nur Token-Validierung + Logging).
- **Anfrage:** „wo Token in .env?" → Zeile 31 `VPN_API_KEY`; Token live als gültig
  verifiziert; Service-Username angezeigt.

## 8. VPN Option B — SOCKS5-Tunneling
**Anfrage:** „baue Option B ein" → Scraper-`requests` laufen über NordVPN-SOCKS5
(`get_proxies`, Fail-Safe). Live: echte IP → NordVPN-NL-IP.
**Anfrage:** „Browser-Jobs/Downloads absichern" → **lokale SOCKS5-Brücke**
(`socks_bridge.py`), da Chromium kein SOCKS5-mit-Auth kann. Live verifiziert.
**Anfrage:** „Vorteil NordLynx?" → erklärt, bewusst zurückgestellt.

## 9. VPN-Frontend + Bereinigung
**Anfrage:** „Frontend: Serverstandort, direkte + VPN-IP, Länder-Dropdown, an/aus,
Echtzeit" → Live-Panel in Einstellungen → VPN; Endpunkte `/api/vpn/connection`,
`/api/vpn/config`.
**Anfrage:** „alte VPN-Einstellungen bereinigen, nur SOCKS5 behalten" → CLI/OpenVPN-
Reste entfernt (Config, `get_vpn_status`/`connect`/`disconnect`/`rotate`,
`models/vpn.py`, `schemas/vpn.py`, alte Frontend-Hooks).

## 10. Memory eingerichtet
**Anfrage:** „merkst du dir das beim Schließen?" → dateibasiertes Memory erklärt;
**Anfrage:** „ja speichern" → `MEMORY.md` + `code-analysis.md` + `vpn-socks5.md`
(später `ml-models.md`).

## 11. Kritische Befunde abgearbeitet
- **#1 Thread-Safety** (Commit a4f99f8): `threading.Lock` + atomares check-and-set
  für alle Status-Dicts; double-checked Model-Loading; Snapshot-Getter.
- **#2 Upload-Limit + #3 toter Code** (Commit 6992149): `MAX_UPLOAD_SIZE_MB`
  durchgesetzt (413) + MIME-Check + Dateiname-Sanitisierung; `app.py`/`schema.sql`
  gelöscht (inkl. Dockerfile/Doku).
- **#4 v1/v2** (Commit 6117984, Option A): v2 ships/images = einzige Lese-Wahrheit;
  `stats.py` auf v2; v1-`/api/ships` entfernt; **DB komplett gelöscht und frisch
  aus dem ORM neu angelegt** (Backup `schiffs-scraper.db.backup`).
- **#5 ML-Leaks** (Commit 2001741): `Image.open` per Context-Manager; Modell nach
  Training freigegeben (`del`+`gc`).
→ **Alle 5 kritischen Befunde behoben.**

## 12. ML-Kette ausgebaut
**Beratung:** drei Teilprobleme (Detektion / Bauart / spezifisches Schiff);
DINOv2-Embeddings statt Klassifikation für Re-ID; ViT bleibt für Bauart.
Hardware: RTX 3070 (Laptop) + optional stärker.

- **DINOv2-Ähnlichkeit** (Commit 548554e): `embedding_service`, `model=dinov2|vit`,
  **Konfidenz + Open-Set-Schwelle**. Live: Flugzeugträger matcht sich selbst 1.0,
  Yacht 0.31.
- **Persistente FAISS-Galerie** (Commit 797c403): Index auf Platte, schnelle Suche,
  `reindex`, optional inkrementell beim Scrapen (`EMBEDDING_AUTO_INDEX`).
- **Frontend-Seite „Wiedererkennung"** (Commit e9c42c4): Foto-Upload-Suche +
  Konfidenz, „Galerie neu aufbauen", Upload-Endpunkt.
- **ArcFace-Fine-Tuning** (Commit b3ce6a6): `reid.py` lernt schiffsspezifische
  Projektion auf DINOv2-Features; Readiness/Train/Status; Frontend-Karte.
- **ML-Doku** (Commit 9ec9453): `/api/docs/ml` + Sektion in der Doku-Seite, mit
  Live-Config-Werten.
- **OCR-Kanal** (Commit 50051f6): zweite Option **`dinov2_ocr`** = identische
  visuelle Suche + OCR-Abgleich (EasyOCR); visuelle Erkennung strikt unverändert.
  Live verifiziert; `verbose=False`-Fix gegen Windows-Konsole-Crash.

## 13. EasyOCR-Installation geklärt
**Anfrage:** „muss ich EasyOCR installieren, Python oder extern?" → Python-Paket
(pip, im venv), kein externes Programm; bereits installiert (1.7.2) + Modelle im
Cache.

---

## Branch & Repo
- Branch `develop`, Remote `PandorasBoxx99/ship-recognition`.
- Architektur am Ende: Detektion (Faster R-CNN) → Bauart (ViT) → spezifisches
  Schiff (DINOv2 + FAISS, optional ArcFace-verfeinert, optional OCR-Abgleich);
  v1 jobs/items = Scrape-Queue, v2 ships/images = Lese-Wahrheit; VPN = NordVPN
  SOCKS5 (requests + Browser-Brücke).
