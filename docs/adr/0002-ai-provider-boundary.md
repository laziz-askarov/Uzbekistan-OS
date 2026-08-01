# ADR 0002: AI provider boundary and response state

- Status: Accepted for foundation; model routing remains configurable
- Date: 2026-07-31

## Context

The product needs streaming, structured outputs, conversation continuity, observable model usage, and evidence validation while retaining model independence and explicit privacy controls.

## Decision

- Use an application-owned AI gateway interface rather than calling provider SDKs from routes or domain logic.
- Use the OpenAI Responses API in its adapter, with typed streaming events and structured outputs.
- Default to `store: false`; Uzbekistan OS remains the system of record for conversations and sends only the bounded context needed for a turn.
- Keep the model identifier, reasoning effort, retention behavior, timeouts, and budgets in configuration and prompt/model registries.
- Validate provider outputs against the application answer schema and evidence pack before emitting a completed application response.

## Consequences

- Provider-specific event types must be translated to the Uzbekistan OS SSE contract.
- Conversation summaries and context-window management are application responsibilities.
- Provider response IDs may be recorded for observability but are not canonical conversation state.
- Model changes require benchmark approval rather than code changes in product workflows.

