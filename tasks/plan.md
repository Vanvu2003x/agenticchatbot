# Implementation Plan: DeepSeek Agent Chat

## Architecture

Vite serves React/assistant-ui and proxies `/api` to local FastAPI. LangGraph runs a LangMem learning node followed by a DeepSeek answer node. SQLite holds durable memories, conversation history and reference text. The browser provides its key in each request; the server forwards only to DeepSeek's fixed API URL and does not persist credentials.

## Phases

1. Establish package scripts, API contract, and proxy validation.
2. Build the accessible chat interface and connect it to the proxy.
3. Verify with unit tests, a production build, and a local browser smoke test.

## Risks

| Risk | Mitigation |
| --- | --- |
| API key leakage | Never save or log it; redact server errors. |
| Prompt injection in model output | Render response as text only. |
| Invalid external requests | Limit body size, message size, and agent allowlist. |
