# GREAT_CHURCH_AI Architecture

## Goal
Build a reliable realtime assistant for church media operators.

## Core flow
1. Capture live audio.
2. Stream audio to transcription.
3. Normalize realtime events.
4. Detect Scripture, sermon context, and media opportunities.
5. Present suggestions to the media operator.
6. Require explicit operator approval before external media actions.
7. Record actions for audit and debugging.

## Human approval boundary
AI suggestions must not directly control a public presentation, projector, livestream, or broadcast output in the initial product. The operator dashboard is the approval boundary.

## Initial event types
- transcript.partial
- transcript.final
- scripture.detected
- context.updated
- media.suggestion.created
- media.suggestion.updated
- media.action.approved
- media.action.rejected
- system.error

## Reliability
Realtime components must tolerate provider failures, disconnects, duplicate events, delayed events, and partial transcripts. External actions should be idempotent.

## Security
Secrets remain server-side. Operator actions require authorization and are auditable. External credentials never ship to the web client.