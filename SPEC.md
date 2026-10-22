# Spec: DeepSeek Agent Chat

## Objective

Provide a local, single-owner DeepSeek chatbot that learns durable instructions and preferences from normal conversation using LangMem and LangGraph. The user supplies their own DeepSeek API key at runtime. This supersedes the initial persona-only prototype.

## User flow

1. Open the local application.
2. Paste a DeepSeek API key into a masked field.
3. Chat normally or teach lasting preferences using natural language.
4. See actual saved memory changes, start another chat and reuse the preferences.
5. Correct or ask to forget memories; add reference text or dialogue examples.

## Security and boundaries

- The API key is held only in browser memory for the current page session; it is not written to disk, browser storage, logs, or source control.
- Browser requests go to a local server endpoint, which forwards the key to DeepSeek for that request only.
- SQLite persists memories, chat history and reference text on the local machine.
- This version has no user accounts, public deployment or token streaming.
- Memory extraction changes stored context, not the model weights.

## Tech stack and commands

- React + TypeScript + Vite + assistant-ui client
- Python FastAPI backend, LangMem extraction, LangGraph workflow, SQLite storage
- Test: `npm test`
- Development: `npm run dev`
- Production build: `npm run build`
- Backend tests: `.\.venv\Scripts\python.exe -m pytest backend -q`

## Success criteria

- A user can paste a DeepSeek key and receive a response.
- LangMem can add, update and delete durable memories, with actual saved-change notices.
- Memories persist across application restarts and separate conversations.
- Pasted knowledge and dialogue examples can be stored, retrieved and deleted.
- An empty or invalid key gets a helpful in-app error.
- The key is never persisted by the application.
- The layout works from a narrow phone viewport through desktop.
