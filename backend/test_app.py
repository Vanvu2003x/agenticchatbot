import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI
from . import app as app_module
from . import engine
from .engine import LearnedMemory
from .store import Store


@pytest.fixture
def local_store(tmp_path):
    return Store(tmp_path / 'test.sqlite3')


@pytest.fixture
def client(local_store, monkeypatch):
    monkeypatch.setattr(app_module, 'store', local_store)
    return TestClient(app_module.app)


def record(rid, content, kind='preference'):
    return SimpleNamespace(id=rid, content=LearnedMemory(kind=kind, content=content))


def test_memory_updates_in_place_and_survives_restart(local_store):
    rid = str(uuid4())
    local_store.apply_memories([record(rid, 'Trả lời ngắn')])
    changes = local_store.apply_memories([record(rid, 'Trả lời chi tiết')])
    reopened = Store(local_store.path)
    assert reopened.memories() == [{'id': rid, 'kind': 'preference', 'content': 'Trả lời chi tiết'}]
    assert changes[0]['action'] == 'updated'
    reopened.delete_memory(rid)
    assert Store(local_store.path).memories() == []


def test_memory_batch_rolls_back_on_capacity_limit(local_store):
    local_store.apply_memories([record(str(uuid4()), str(i)) for i in range(100)])
    with pytest.raises(ValueError):
        local_store.apply_memories([record(str(uuid4()), 'Overflow')])
    assert len(local_store.memories()) == 100


def test_retrieval_handles_unaccented_vietnamese_and_unrelated_queries(local_store):
    local_store.add_knowledge('Học phí', 'document', 'Học phí robotics là 500.000 đồng.')
    assert local_store.retrieve('hoc phi robotics')[0]['title'] == 'Học phí'
    assert not local_store.retrieve('astronaut')


def test_foreign_origin_is_blocked(client):
    assert client.get('/api/state', headers={'Origin': 'https://evil.example'}).status_code == 403


def test_chat_requires_key_before_any_inference(client):
    result = client.post('/api/chat', json={'conversation_id': str(uuid4()), 'message': 'Hello'})
    assert result.status_code == 401


def test_bad_request_does_not_echo_input(client):
    result = client.post('/api/chat', json={'conversation_id': 'secret-input', 'message': ''})
    assert result.status_code == 422
    assert 'secret-input' not in result.text


def test_knowledge_roundtrip_and_deletion(client):
    result = client.post('/api/knowledge', json={'title': 'Tư vấn', 'kind': 'example', 'content': 'Khách: Giá bao nhiêu?\nBot: Bạn cần gì?'})
    rid = result.json()['id']
    assert client.get('/api/state').json()['knowledge'][0]['kind'] == 'example'
    assert client.delete('/api/knowledge/' + rid).status_code == 200
    assert not client.get('/api/state').json()['knowledge']


def test_langmem_and_graph_extract_persist_and_recall(local_store, monkeypatch):
    """Run real LangMem/Trustcall/LangGraph; stub only the remote DeepSeek boundary."""
    calls = []

    def transport(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if payload.get('tools'):
            message = {'role': 'assistant', 'content': '', 'tool_calls': [{
                'id': 'call_memory_1', 'type': 'function', 'function': {
                    'name': 'LearnedMemory', 'arguments': json.dumps({'kind': 'preference', 'content': 'Người dùng thích câu trả lời ngắn gọn.'})}}]}
        else:
            assert 'Người dùng thích câu trả lời ngắn gọn.' in payload['messages'][0]['content']
            message = {'role': 'assistant', 'content': 'Đã nhớ, mình sẽ trả lời ngắn gọn.'}
        return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 1, 'model': 'deepseek-flash', 'choices': [{'index': 0, 'message': message, 'finish_reason': 'tool_calls' if payload.get('tools') else 'stop'}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http_client:
            monkeypatch.setattr(engine, 'ChatOpenAI', lambda **kwargs: ChatOpenAI(**kwargs, http_async_client=http_client))
            request = SimpleNamespace(model='deepseek-flash', remember=True, conversation_id=str(uuid4()), message='Từ giờ trả lời ngắn gọn nhé')
            result = await engine.run_chat(local_store, request, 'fake-key-for-testing')
            assert result['changes'][0]['action'] == 'added'
            assert not result['warning']
            request.conversation_id = str(uuid4())
            request.message = 'Tôi thích bạn trả lời thế nào?'
            request.remember = False
            await engine.run_chat(Store(local_store.path), request, 'fake-key-for-testing')
    asyncio.run(run())
    assert len(calls) == 3
    assert 'fake-key-for-testing' not in open(local_store.path, 'rb').read().decode('utf-8', errors='ignore')


def test_memory_failure_is_visible_but_answer_still_works(local_store, monkeypatch):
    class BrokenManager:
        async def ainvoke(self, data):
            raise RuntimeError('secret error')
    monkeypatch.setattr(engine, 'create_memory_manager', lambda *args, **kwargs: BrokenManager())
    class FakeChat:
        async def ainvoke(self, messages):
            return SimpleNamespace(content='Xin chào')
    monkeypatch.setattr(engine, 'ChatOpenAI', lambda **kwargs: FakeChat())
    result = asyncio.run(engine.run_chat(local_store, SimpleNamespace(model='deepseek-flash', remember=True, conversation_id=str(uuid4()), message='Hãy nhớ tôi thích trà'), 'fake-key'))
    assert result['warning'] and not result['changes']
    assert result['answer'] == 'Xin chào'
    assert 'secret error' not in result['warning']


@pytest.mark.parametrize('operation', ['update', 'delete'])
def test_real_langmem_modifies_existing_memory(local_store, monkeypatch, operation):
    rid = str(uuid4())
    local_store.apply_memories([record(rid, 'Trả lời ngắn')])

    def transport(request):
        payload = json.loads(request.content)
        if payload.get('tools'):
            name = 'PatchDoc' if operation == 'update' else 'RemoveDoc'
            arguments = {'json_doc_id': rid}
            if operation == 'update':
                arguments.update(planned_edits='Replace content with the new preference.', patches=[{'op': 'replace', 'path': '/content', 'value': 'Trả lời chi tiết'}])
            message = {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'call_change', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
        else:
            message = {'role': 'assistant', 'content': 'Xong.'}
        return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 1, 'model': 'deepseek-flash', 'choices': [{'index': 0, 'message': message, 'finish_reason': 'stop'}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http_client:
            monkeypatch.setattr(engine, 'ChatOpenAI', lambda **kwargs: ChatOpenAI(**kwargs, http_async_client=http_client))
            result = await engine.run_chat(local_store, SimpleNamespace(model='deepseek-flash', remember=True, conversation_id=str(uuid4()), message='Đổi sang trả lời chi tiết' if operation == 'update' else 'Quên sở thích trả lời ngắn đi'), 'fake-key')
            assert not result['warning']
            assert result['changes'][0]['action'] == ('updated' if operation == 'update' else 'deleted')
    asyncio.run(run())
    if operation == 'delete':
        assert not local_store.memories()
    else:
        assert local_store.memories()[0]['content'] == 'Trả lời chi tiết'
