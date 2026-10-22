"""Single-owner local persistence. Credentials never enter this module."""
import re
import sqlite3
import unicodedata
from pathlib import Path
from uuid import uuid4


def words(text):
    normalized = unicodedata.normalize('NFD', text.lower()).replace('đ', 'd')
    return set(re.findall(r'[a-z0-9]{2,}', ''.join(c for c in normalized if not unicodedata.combining(c))))


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, kind TEXT, content TEXT);
                CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT, updated TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS messages (seq INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT, role TEXT, content TEXT);
                CREATE TABLE IF NOT EXISTS knowledge (id TEXT PRIMARY KEY, title TEXT, kind TEXT, content TEXT);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def rows(self, sql, args=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args)]

    def memories(self):
        return self.rows('SELECT * FROM memories ORDER BY rowid')

    def apply_memories(self, records):
        """Atomically apply a validated LangMem change batch."""
        changes = []
        with self.connect() as db:
            for record in records:
                rid, value = record.id, record.content
                previous = db.execute('SELECT * FROM memories WHERE id=?', (rid,)).fetchone()
                if value.__class__.__name__ == 'RemoveDoc':
                    if previous:
                        db.execute('DELETE FROM memories WHERE id=?', (rid,))
                        changes.append({'action': 'deleted', 'content': previous['content']})
                    continue
                data = value.model_dump()
                if not previous or previous['content'] != data['content'] or previous['kind'] != data['kind']:
                    db.execute('INSERT OR REPLACE INTO memories VALUES (?,?,?)', (rid, data['kind'], data['content']))
                    changes.append({'action': 'updated' if previous else 'added', 'content': data['content']})
            if db.execute('SELECT count(*) FROM memories').fetchone()[0] > 100:
                raise ValueError('Bộ nhớ đầy (100 mục). Hãy xóa các mục cũ rồi thử lại.')
        return changes

    def delete_memory(self, rid):
        with self.connect() as db:
            db.execute('DELETE FROM memories WHERE id=?', (rid,))

    def conversation(self, cid):
        return self.rows('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY seq', (cid,))

    def save_turn(self, cid, user, assistant):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO conversations(id,title) VALUES (?,?)', (cid, user[:65]))
            db.executemany('INSERT INTO messages(conversation_id,role,content) VALUES (?,?,?)', [(cid, 'user', user), (cid, 'assistant', assistant)])
            db.execute('UPDATE conversations SET updated=CURRENT_TIMESTAMP WHERE id=?', (cid,))

    def add_knowledge(self, title, kind, content):
        rid = str(uuid4())
        with self.connect() as db:
            if db.execute('SELECT count(*) FROM knowledge').fetchone()[0] >= 100:
                raise ValueError('Kho đã có 100 tài liệu. Hãy xóa tài liệu cũ.')
            db.execute('INSERT INTO knowledge VALUES (?,?,?,?)', (rid, title, kind, content))
        return rid

    def retrieve(self, query):
        terms = words(query)
        candidates = []
        for item in self.rows('SELECT * FROM knowledge'):
            for index, start in enumerate(range(0, len(item['content']), 2000)):
                chunk = item['content'][start:start + 2400]
                score = len(terms & words(item['title'] + ' ' + chunk))
                if score:
                    candidates.append((score, {**item, 'content': chunk, 'chunk': index + 1}))
        return [item for _, item in sorted(candidates, key=lambda pair: pair[0], reverse=True)[:4]]
