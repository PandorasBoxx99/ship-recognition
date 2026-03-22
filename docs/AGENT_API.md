# Agent API Dokumentation

Die Agent API ermoeglicht die autonome Steuerung des Ship Recognition Systems durch KI-Agenten.

## Authentifizierung

Wenn `SECRET_KEY` in `.env` gesetzt ist (nicht der Default-Wert), muss der Header `X-API-Key` mitgesendet werden.

## Endpunkte

### System-Kontext

**GET `/api/agent/context`**

Liefert den vollstaendigen Systemzustand: Datenmengen, aktives Modell, laufende Jobs, Typverteilung, Datenluecken.

### Faehigkeiten

**GET `/api/agent/capabilities`**

Liste aller verfuegbaren Aktionen mit Parameterbeschreibung.

### Aktion ausfuehren

**POST `/api/agent/action`**

```json
{
  "action": "predict",
  "params": {"image_path": "/pfad/zum/bild.jpg"}
}
```

Verfuegbare Aktionen:
- `run_scraper` — Scraping-Job starten (`job_id`)
- `train_model` — Training starten (`dataset_dir`, `epochs`, `batch_size`, `learning_rate`)
- `predict` — Einzelbild klassifizieren (`image_path`)
- `generate_synthetic` — Synthetische Daten erzeugen (`source_dir`, `num_per_image`)
- `rebuild_dataset` — Dataset-Statistiken abrufen

### Training

- **POST `/api/agent/training/start`** — Training starten
- **GET `/api/agent/training/status`** — Training-Status

### Dataset

- **POST `/api/agent/dataset/build`** — Dataset-Statistiken
- **POST `/api/agent/dataset/augment`** — Augmentation starten

### Inferenz

**POST `/api/agent/inference`**

```json
{"image_path": "/pfad/zum/bild.jpg"}
```

### Self-Improvement

**POST `/api/agent/improve`**

```json
{
  "goal": "improve_accuracy",
  "constraints": {"max_training_time": "2h"}
}
```

Analysiert das System und gibt Verbesserungsvorschlaege zurueck:
- Datenluecken (Klassen mit wenigen Bildern)
- Unklassifizierte Bilder
- Modell-Status

## Response-Format

```json
{
  "status": "success",
  "data": { ... }
}
```

Fehler:
```json
{
  "status": "error",
  "errors": [{"code": "MODEL_NOT_FOUND", "message": "..."}]
}
```
