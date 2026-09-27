# Realtime Event Contract

Every realtime event uses a versioned envelope:

```json
{
  "id": "uuid",
  "type": "transcript.final",
  "version": 1,
  "timestamp": "2026-01-01T00:00:00Z",
  "session_id": "uuid",
  "payload": {}
}
```

The contract is intentionally provider-neutral so transcription, AI, presentation, and broadcast vendors can be replaced without changing the product's core event model.