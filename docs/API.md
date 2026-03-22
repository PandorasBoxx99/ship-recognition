# API-Dokumentation

Basis-URL: `http://localhost:3025`

Interaktive Swagger-Docs: `http://localhost:3025/docs`

## Standardisiertes Response-Format

Erfolg: HTTP 200/201 mit JSON-Body.
Fehler: HTTP 4xx/5xx mit `{"detail": "Fehlermeldung"}`.

---

## VPN (`/api/vpn`)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/vpn/status` | VPN-Verbindungsstatus |
| POST | `/api/vpn/connect` | VPN verbinden (`{"country": "Germany"}`) |
| POST | `/api/vpn/disconnect` | VPN trennen |
| POST | `/api/vpn/rotate` | IP wechseln |

## Scraper (`/api`)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/analyze` | Website analysieren (`{"url": "..."}`) |
| GET | `/api/jobs` | Alle Jobs auflisten |
| POST | `/api/jobs` | Neuen Job erstellen |
| GET | `/api/jobs/{id}` | Job-Details mit Items |
| POST | `/api/jobs/{id}/start` | Job starten |
| POST | `/api/jobs/{id}/pause` | Job pausieren |
| DELETE | `/api/jobs/{id}/delete` | Job loeschen |

## Schiffe v1 (`/api/ships`) — Legacy

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/ships` | Schiffe auflisten (Paginierung, Filter) |
| GET | `/api/ships/{id}` | Schiff-Details |
| GET | `/api/ships/stats` | Typ-Statistiken |

## Schiffe v2 (`/api/v2/ships`) — Normalisiert

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/v2/ships` | Schiffe auflisten (normalisiert) |
| GET | `/api/v2/ships/{id}` | Schiff mit Bildern und Aliasen |
| POST | `/api/v2/ships` | Neues Schiff anlegen |
| PUT | `/api/v2/ships/{id}` | Schiff bearbeiten |
| DELETE | `/api/v2/ships/{id}` | Schiff loeschen |
| GET | `/api/v2/ships/{id}/images` | Bilder eines Schiffs |
| POST | `/api/v2/ships/{id}/aliases` | Alias hinzufuegen |

## Klassifikation (`/api`)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/classify` | Bild hochladen und klassifizieren |
| POST | `/api/classify/ship/{id}` | Bestehendes Schiff klassifizieren |
| POST | `/api/classify/batch` | Batch-Klassifikation starten |
| GET | `/api/classify/batch/status` | Batch-Status |
| GET | `/api/model/info` | Modell-Informationen |
| GET | `/api/classifications` | Klassifikations-Historie |

## Modell-Registry (`/api/models`)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/models` | Alle Modelle auflisten |
| GET | `/api/models/{id}` | Modell-Details |
| POST | `/api/models` | Modell registrieren |
| POST | `/api/models/{id}/activate` | Modell aktivieren |

## Training (`/api/training`)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/training/status` | Training-Status |
| POST | `/api/training/start` | Training starten |
| GET | `/api/training/datasets` | Verfuegbare Datasets |

## Augmentation (`/api/augment`)

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/augment` | Augmentation starten |
| GET | `/api/augment/status` | Augmentation-Status |

## Statistiken & Einstellungen

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/stats` | Dashboard-Statistiken |
| GET | `/api/urls` | Vordefinierte URLs |
| POST | `/api/urls` | URL hinzufuegen |
| DELETE | `/api/urls/{id}` | URL loeschen |
