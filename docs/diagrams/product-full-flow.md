# Product Diagrams — Full Product Sequence

**Source:** `PRD-ReunionAI.md`, section 44 (verbatim Mermaid extraction).

End-to-end sequence: meeting creation, audio upload, STT job, AI processing,
document OCR, minutes drafting, human review, approval, notification, and
publication.

```mermaid
sequenceDiagram
    actor Usuario
    participant Frontend
    participant API
    participant DB as PostgreSQL
    participant Queue as Redis/Queue
    participant Worker
    participant STT as Whisper
    participant OCR
    participant AI
    participant Storage
    participant Email

    Usuario->>Frontend: Crea reunión
    Frontend->>API: Crear reunión
    API->>DB: Persistir reunión

    Usuario->>Frontend: Carga audio
    Frontend->>API: Upload
    API->>Storage: Guardar original
    API->>Queue: Crear job STT

    Queue->>Worker: Procesar audio
    Worker->>STT: Transcribir
    STT-->>Worker: Segmentos
    Worker->>DB: Guardar transcripción
    Worker->>AI: Procesar contenido
    AI-->>Worker: Resumen/acuerdos/tareas
    Worker->>DB: Guardar resultados

    Usuario->>Frontend: Carga documento
    Frontend->>API: Upload documento
    API->>Storage: Guardar original
    API->>Queue: Crear job OCR

    Queue->>Worker: Procesar OCR
    Worker->>OCR: Extraer texto
    OCR-->>Worker: Texto OCR
    Worker->>DB: Guardar resultado

    Usuario->>Frontend: Solicita borrador
    Frontend->>API: Generar acta
    API->>AI: Crear borrador
    AI-->>API: Acta
    API->>DB: Guardar versión

    Usuario->>Frontend: Revisa
    Frontend->>API: Correcciones
    API->>DB: Nueva versión

    Usuario->>Frontend: Aprueba
    Frontend->>API: Aprobar
    API->>DB: Registrar aprobación

    API->>Email: Notificar
    API->>DB: Publicar acta
    Frontend-->>Usuario: Acta disponible
```
