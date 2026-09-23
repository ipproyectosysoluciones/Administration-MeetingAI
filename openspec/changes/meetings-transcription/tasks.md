# Tasks — meetings-transcription

| Task | Slice | Tipo | Alcance | Gates |
|---|---|---|---|---|
| ~~TASK-300~~ | T1 | feat | migration 0007 transcriptions + transcription.* seeds | tests_migrations_0007 |
| ~~TASK-301~~ | T2 | feat | SpeechToTextProvider + FasterWhisperProvider (unit, no downloads en CI) | unit |
| ~~TASK-302~~ | T3 | feat | transcription service + worker loop (claim-next, skip-if-draft) | integration |
| ~~TASK-303~~ | T3 | feat | enqueue process_recording desde recordings upload | integration |
| ~~TASK-304~~ | T4 | feat | REST read-only: GET /transcriptions/{id}, GET /recordings/{id}/transcriptions | integration |
| ~~TASK-305~~ | T5 | chore | Docker compose worker service + README docs + apply-progress | docs |

Convenciones: TDD estricto (RED → GREEN → REFACTOR); each slice ≤400 líneas de producción; Conventional Commits; no push/merge desde el apply (padre orquesta).
