"""One live LangMem extraction request, without any persistence."""
import asyncio
import getpass
import json
import re
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI
from langmem import create_memory_manager
from .engine import LearnedMemory, MEMORY_INSTRUCTIONS
from .store import Store


async def main(key):
    store = Store(Path(__file__).resolve().parents[1] / 'data/chat.sqlite3')
    model = ChatOpenAI(model='deepseek-chat', api_key=key, base_url='https://api.deepseek.com', timeout=40, max_retries=0, extra_body={'thinking': {'type': 'disabled'}})
    manager = create_memory_manager(model, schemas=[LearnedMemory], instructions=MEMORY_INSTRUCTIONS, enable_deletes=True)
    try:
        result = await manager.ainvoke({'messages': [{'role': 'user', 'content': 'Hãy nhớ quy tắc thử nghiệm: trả lời bắt đầu bằng CHAO-2026 trong mọi chat mới.'}], 'existing': [(m['id'], 'LearnedMemory', {'kind': m['kind'], 'content': m['content']}) for m in store.memories() if m['kind'] == 'instruction'], 'max_steps': 1})
        print(json.dumps({'ok': True, 'extracted': len(result)}, ensure_ascii=False))
    except Exception as e:
        safe = str(e).replace(key, '[REDACTED]')
        safe = re.sub(r'sk-[a-zA-Z0-9_-]+', '[REDACTED]', safe)
        print(json.dumps({'ok': False, 'type': type(e).__name__, 'status': getattr(e, 'status_code', None), 'reason': safe[:1200]}, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main(getpass.getpass('DeepSeek key (hidden): ').strip()))
