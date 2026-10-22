# Aster — DeepSeek with teachable memory

A local, single-owner chatbot using **assistant-ui + LangGraph + LangMem + DeepSeek**. The React interface is in Vietnamese.

## Current status

This is an experimental local build. Live testing on 22/10/2026 found that memory updates can fail when LangMem returns unchanged entries as dictionaries, and keyword retrieval can miss a known tuition price. These issues have not yet been fixed. See [the live evaluation](docs/live-evaluation-2026-10-22.md). The passing automated tests cover narrower cases and do not establish that every live teaching operation works.

## Start on this machine

```powershell
cd 'C:\Users\Vanvu\Desktop\AI Chat\deepseek-agent-chat'
npm run dev
```

Open http://127.0.0.1:5173, choose **Kết nối DeepSeek**, and enter your API key. Keys stay in React memory and travel only to the local proxy and the fixed HTTPS DeepSeek endpoint. Reloading the page clears the key. Chat, documents, and extracted memories are stored in `data/chat.sqlite3`.

## Try teaching

1. Say: `Từ giờ hãy trả lời ngắn gọn bằng tiếng Việt. Hỏi nhu cầu trước khi tư vấn.`
2. A green saved-change notice confirms the actual database write. Inspect **Bộ nhớ**.
3. Start a new conversation and ask for advice. The saved instructions are included automatically.
4. Say: `Đổi lại: tôi muốn trả lời chi tiết, có ví dụ.`
5. Say: `Quên sở thích về độ dài câu trả lời đi.` Or click **Quên** beside a memory.
6. Restart the application: memories remain, but enter your API key again.

Chat normally to teach preferences and enduring facts. Temporary requests such as `chỉ câu này viết ngắn lại` are instructed not to become permanent memories. Extraction is model-dependent; inspect the saved-change notices and memory page, rather than relying on a model's promise alone.

**Kiến thức & chat mẫu** accepts pasted text and UTF-8 TXT/Markdown/CSV/JSON files. Choose whether the content is factual reference material or a dialogue example. Retrieval currently uses accent-insensitive keyword overlap and includes up to four 2,400-character snippets. PDF/Word parsing, embedding search and fine-tuning are not implemented.

## Architecture

- `src/Chat.tsx`: assistant-ui runtime and message/composer primitives; Markdown rendering with raw HTML disabled.
- `src/App.tsx`: navigation, key entry, documents, conversations and memory management.
- `backend/engine.py`: real LangGraph `learn → answer` pipeline. LangMem/Trustcall extracts, patches or removes `LearnedMemory` records using DeepSeek tool calls.
- `backend/store.py`: SQLite transactions for memories, conversations and knowledge; keyword retrieval.
- `backend/app.py`: loopback API with input validation, request-size limit, origin/host restrictions and sanitized errors.

The backend loads up to 24 prior messages per turn and all saved memories (maximum 100). Auto-memory adds a model call on each enabled turn, so teaching increases latency and API usage. Disabling **Tự ghi nhớ** stops writes while still using existing memories. A memory update may succeed before a subsequent response call fails; the UI refreshes memory after both outcomes.

This is a local app for one owner. It does not implement accounts, multi-user separation or production deployment. It binds to `127.0.0.1`. Do not expose its ports as a public service.

## Fresh installation

Requires Node 22+ and Python 3.12+.

```powershell
git clone https://github.com/Vanvu2003x/agenticchatbot.git
cd agenticchatbot
npm ci --ignore-scripts
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm run dev
```

## Load the supplied EasyUp handbook

The handbook is included as source text; the runtime database and private conversation history are not committed. From the project directory, run:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m backend.import_easyup docs/knowledge/easyup-handbook-v2.txt
```

This imports 13 explicit owner rules, 18 reference documents and eight dialogue examples without making a paid model call. Repeating the import replaces only the same EasyUp import IDs. Historical reference prices and offers are marked as needing current confirmation.

## Verification

```powershell
npm test
npm run build
.\.venv\Scripts\python.exe -m pytest backend -q
```

Tests run real LangMem/Trustcall/LangGraph against a mocked DeepSeek HTTP boundary, verifying insert/update/delete, persistence across database reopening, cross-thread recall, failure reporting, input validation and retrieval. They do not establish actual model quality. Live inference needs a user-supplied DeepSeek key.

Dependencies currently emit a Trustcall/LangGraph deprecation warning; it does not prevent the tested pipeline from running. DeepSeek model names follow https://api-docs.deepseek.com/ and are restricted to `deepseek-flash` and `deepseek-v4-pro`.
