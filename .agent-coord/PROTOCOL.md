# Agent Coordination Protocol v1

## Execution Modes

| Mode | Beschreibung | Wann |
|------|-------------|------|
| 🔒 SERIAL | Ein Agent, Rest wartet | Default - SICHER |
| ⚡ PARALLEL | Mehrere gleichzeitig | Nur bei Freigabe |
| 🔄 STAGED | Vorarbeit möglich | Klare Trennung |

**Default: SERIAL** - Sicherheit vor Geschwindigkeit!

## Workflow

1. **WORKFLOW.md lesen** - Welche Phase? Bin ich dran?
2. **Lock erstellen** - `locks/{agent-name}.lock`
3. **Arbeiten + Committen** - Kleine, atomare Commits
4. **Lock löschen + Log schreiben** - In `logs/{agent}-{datum}.md`
5. **Review anfordern** (optional) - In `reviews/`

## Lock-Format

```json
{
  "agent": "agent-name",
  "started": "2026-02-15T10:45:00Z",
  "files": ["datei1.py", "datei2.html"],
  "task": "task-001",
  "mode": "serial",
  "blocks": ["andere-agents"],
  "eta_minutes": 15
}
```

## Task-Lifecycle

1. `task-XXX-open.json` → Wartet
2. `task-XXX-locked-{agent}.json` → Agent arbeitet (GESPERRT!)
3. `task-XXX-done.json` → Fertig
4. `task-XXX-reviewed.json` → Geprüft (optional)

## Regeln

- Wer zuerst Lock hat, arbeitet
- Stuck Lock (>30 Min ohne Commit): Darf übernommen werden
- Bei Merge-Konflikten: Pusher muss resolven
- Immer `git pull` vor Lock erstellen
