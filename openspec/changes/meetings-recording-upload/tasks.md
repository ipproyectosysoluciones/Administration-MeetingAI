# Tasks — meetings-recording-upload

| Task | Slice | Type | Description | Tests |
|---|---|---|---|---|
| TASK-250 | S1 | feat | Migration 0006 (recordings + jobs) + recording.* permissions seed + base-role mapping | migration smoke + seed count/idempotency |
| TASK-251 | S2 | feat | StorageProvider protocol + LocalStorageProvider + unit tests | unit |
| TASK-252 | S3 | feat | recordings service (tenant-scoped lookup incl. meeting indirection) + REST router | integration |
| TASK-253 | S4 | feat | jobs module service (enqueue/mark helpers) + transaccionalidad upload/job | integration |
| TASK-254 | S4 | feat | frontend Portal recordings (list/download inside meeting) | vitest |
| TASK-255 | S4 | chore | docs + PR merge to develop, sync main rules | docs |
