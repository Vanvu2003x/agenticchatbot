import asyncio
import os
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from openai import AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError, APIStatusError
from pydantic import BaseModel, Field, field_validator
from .engine import run_chat
from .store import Store

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
store = Store(os.environ.get('CHAT_DB', str(Path(__file__).resolve().parents[1] / 'data/chat.sqlite3')))
lock = asyncio.Lock()


@app.middleware('http')
async def local_boundary(request: Request, call_next):
    if request.headers.get('origin') not in (None, 'http://127.0.0.1:5173', 'http://localhost:5173'):
        return JSONResponse({'error': 'Origin không được phép.'}, status_code=403)
    if request.method in ('POST', 'PUT', 'PATCH'):
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 500_000:
                return JSONResponse({'error': 'Dữ liệu quá lớn (tối đa 500 KB).'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # Never echo request bodies or headers in validation errors.
    return JSONResponse({'error': 'Dữ liệu không hợp lệ. Kiểm tra độ dài, model và nội dung.'}, status_code=422)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=12000)
    model: Literal['deepseek-flash', 'deepseek-v4-pro'] = 'deepseek-flash'
    remember: bool = True

    @field_validator('conversation_id')
    @classmethod
    def valid_id(cls, value):
        return str(UUID(value))

    @field_validator('message')
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError('Tin nhắn trống')
        return value.strip()


class KnowledgeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    kind: Literal['document', 'example']
    content: str = Field(min_length=1, max_length=200000)

    @field_validator('title', 'content')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Nội dung trống')
        return value.strip()


@app.get('/api/state')
async def state():
    return {'memories': store.memories(),
        'conversations': store.rows('SELECT * FROM conversations ORDER BY updated DESC, rowid DESC'),
        'knowledge': store.rows('SELECT id,title,kind,length(content) AS size FROM knowledge ORDER BY rowid DESC')}


@app.get('/api/conversations/{cid}')
async def conversation(cid: UUID):
    return store.conversation(str(cid))


@app.delete('/api/memories/{rid}')
async def delete_memory(rid: UUID):
    async with lock:
        store.delete_memory(str(rid))
    return {'ok': True}


@app.post('/api/knowledge')
async def add_knowledge(data: KnowledgeRequest):
    async with lock:
        try:
            rid = store.add_knowledge(data.title, data.kind, data.content)
        except ValueError as error:
            raise HTTPException(400, str(error))
    return {'id': rid}


@app.delete('/api/knowledge/{rid}')
async def delete_knowledge(rid: UUID):
    async with lock:
        with store.connect() as db:
            db.execute('DELETE FROM knowledge WHERE id=?', (str(rid),))
    return {'ok': True}


@app.post('/api/chat')
async def chat(data: ChatRequest, authorization: str = Header(default='')):
    if not authorization.startswith('Bearer ') or not (8 <= len(authorization[7:]) <= 256) or any(c.isspace() for c in authorization[7:]):
        return JSONResponse({'error': 'Nhập DeepSeek API key trong phần Kết nối.'}, status_code=401)
    try:
        async with lock:
            return await asyncio.wait_for(run_chat(store, data, authorization[7:]), timeout=190)
    except AuthenticationError:
        return JSONResponse({'error': 'API key không hợp lệ. Kiểm tra lại key DeepSeek.'}, status_code=401)
    except RateLimitError:
        return JSONResponse({'error': 'DeepSeek đang giới hạn lượt gọi. Hãy thử lại sau.'}, status_code=429)
    except (TimeoutError, APITimeoutError):
        return JSONResponse({'error': 'DeepSeek phản hồi quá lâu. Thử lại sau; kiểm tra Bộ nhớ vì phần ghi nhớ có thể đã lưu.'}, status_code=504)
    except APIConnectionError:
        return JSONResponse({'error': 'Không kết nối được DeepSeek. Kiểm tra Internet.'}, status_code=502)
    except APIStatusError as error:
        message = 'Tài khoản DeepSeek không đủ số dư.' if error.status_code == 402 else 'DeepSeek từ chối yêu cầu. Kiểm tra quyền sử dụng model hoặc thử lại.'
        return JSONResponse({'error': message}, status_code=502)
    except Exception:
        return JSONResponse({'error': 'Không hoàn tất được lượt chat. Kiểm tra Bộ nhớ rồi thử lại.'}, status_code=500)
