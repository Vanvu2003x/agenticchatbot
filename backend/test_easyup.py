from .import_easyup import RULES, import_handbook, stable_id
from .store import Store


def test_import_preserves_existing_data_and_is_idempotent(tmp_path):
    source = tmp_path / 'handbook.txt'
    text = 'Cẩm nang v2  ' + '  '.join(
        (f'3. Chỉ tiêu vận hành  Nội dung vận hành' if i == 3 else f'## {i}. Mục {i}  Nội dung {i}')
        for i in range(1, 27)
    )
    # Match the missing section-3 heading in the original pasted format.
    text = text.replace('  3. Chỉ tiêu', '   3. Chỉ tiêu')
    source.write_text(text, encoding='utf-8')
    store = Store(tmp_path / 'chat.sqlite3')
    store.add_knowledge('Existing', 'document', 'Keep me')
    with store.connect() as db:
        db.execute('INSERT INTO memories VALUES (?,?,?)', ('existing', 'fact', 'Keep my memory'))
    first = import_handbook(source, store)
    second = import_handbook(source, store)
    assert first == second
    assert len(store.memories()) == len(RULES) + 1
    assert len(store.rows('SELECT * FROM knowledge')) == 27
    assert next(m for m in store.memories() if m['id'] == 'existing')['content'] == 'Keep my memory'
    assert store.rows('SELECT * FROM knowledge WHERE id=?', (stable_id('section/8'),))[0]['kind'] == 'example'
    assert 'THAM CHIẾU' in RULES['pricing']
    assert 'CHƯA kết nối' in RULES['real-actions']
