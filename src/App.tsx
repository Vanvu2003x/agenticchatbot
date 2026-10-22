import { useEffect, useRef, useState } from 'react';
import Chat from './Chat';
import { api, jsonBody, type Message, type Reply, type State } from './api';

const empty: State = { memories: [], conversations: [], knowledge: [] };
const labels: Record<string, string> = { instruction: 'Cách hỗ trợ', preference: 'Sở thích', fact: 'Về bạn' };
type Page = 'chat' | 'memory' | 'knowledge' | 'settings';

export default function App() {
  const [page, setPage] = useState<Page>('chat');
  const [state, setState] = useState<State>(empty);
  const [key, setKey] = useState('');
  const [model, setModel] = useState('deepseek-flash');
  const [remember, setRemember] = useState(true);
  const [cid, setCid] = useState<string>(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reply, setReply] = useState<Reply | null>(null);
  const [failedText, setFailedText] = useState('');
  const [notice, setNotice] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [kind, setKind] = useState('document');
  const [knowledgeBusy, setKnowledgeBusy] = useState(false);
  const navGeneration = useRef(0);
  const busyGuard = useRef(false);

  async function refresh() { setState(await api<State>('/state')); }
  useEffect(() => { refresh().catch(() => setError('Chưa kết nối được backend. Hãy kiểm tra app đã khởi động.')); }, []);

  async function newChat() {
    if (busyGuard.current) return;
    navGeneration.current++;
    setLoading(false); setCid(crypto.randomUUID()); setMessages([]); setReply(null); setFailedText(''); setError(''); setPage('chat');
  }

  async function openChat(id: string) {
    if (busyGuard.current) return;
    const generation = ++navGeneration.current;
    setLoading(true); setError('');
    try {
      const data = await api<Message[]>('/conversations/' + id);
      if (generation !== navGeneration.current) return;
      setCid(id); setMessages(data); setReply(null); setFailedText(''); setPage('chat');
    } catch (e) { if (generation === navGeneration.current) setError((e as Error).message); }
    finally { if (generation === navGeneration.current) setLoading(false); }
  }

  async function send(text: string) {
    if (busyGuard.current) return;
    if (!key.trim()) { setError('Nhập API key ở mục Kết nối trước nhé.'); setPage('settings'); return; }
    busyGuard.current = true;
    setBusy(true); setError(''); setReply(null); setFailedText('');
    const previous = messages;
    setMessages([...previous, { role: 'user', content: text }]);
    try {
      const result = await api<Reply>('/chat', jsonBody({ conversation_id: cid, message: text, model, remember }, key.trim()));
      setMessages([...previous, { role: 'user', content: text }, { role: 'assistant', content: result.answer }]);
      setReply(result);
    } catch (e) {
      setMessages(previous);
      setFailedText(text);
      setError((e as Error).message + ' Tin nhắn chưa hoàn tất; bạn có thể gửi lại.');
    } finally {
      busyGuard.current = false; setBusy(false);
      refresh().catch(() => setError('Không tải lại được bộ nhớ. Hãy tải lại trang.'));
    }
  }

  async function remove(path: string) {
    try { await api(path, { method: 'DELETE' }); await refresh(); }
    catch (e) { setError((e as Error).message); }
  }

  async function saveKnowledge(event: React.FormEvent) {
    event.preventDefault(); setError(''); setNotice(''); setKnowledgeBusy(true);
    try {
      await api('/knowledge', jsonBody({ title, kind, content }));
      setTitle(''); setContent(''); await refresh(); setNotice('Đã thêm vào kho. Nội dung liên quan sẽ được tìm khi bạn chat.');
    } catch (e) { setError((e as Error).message); }
    finally { setKnowledgeBusy(false); }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setPage('chat'); }}><span className="brand-mark">✳</span> aster<span className="brand-dot">.</span></a>
      <span className="workspace-label">PERSONAL WORKSPACE</span>
      <button className="new-chat" onClick={newChat} disabled={busy}>＋ <span>Cuộc trò chuyện mới</span><span className="shortcut">↗</span></button>
      <nav aria-label="Điều hướng chính">
        <button className={page === 'chat' ? 'nav-item active' : 'nav-item'} onClick={() => setPage('chat')}><span>◫</span> Trò chuyện</button>
        <button className={page === 'memory' ? 'nav-item active' : 'nav-item'} onClick={() => setPage('memory')}><span>✧</span> Bộ nhớ <b>{state.memories.length}</b></button>
        <button className={page === 'knowledge' ? 'nav-item active' : 'nav-item'} onClick={() => setPage('knowledge')}><span>▤</span> Kiến thức & chat mẫu <b>{state.knowledge.length}</b></button>
      </nav>
      <div className="history"><span className="section-label">CUỘC TRÒ CHUYỆN</span>
        {state.conversations.length ? state.conversations.map(item => <button disabled={busy || loading} className={`history-item ${cid === item.id ? 'selected' : ''}`} key={item.id} onClick={() => openChat(item.id)}>{item.title}</button>) : <p className="history-empty">Những ý tưởng hay bắt đầu<br/>từ một cuộc trò chuyện.</p>}
      </div>
      <div className="sidebar-bottom"><div className="memory-card"><span>✧</span><strong>Nhớ điều quan trọng.</strong><p>Bạn có thể dạy, sửa hoặc yêu cầu Aster quên bất cứ lúc nào.</p><button onClick={() => setPage('memory')}>Khám phá bộ nhớ ↗</button></div>
        <button className="profile" onClick={() => setPage('settings')}><span className="avatar">V</span><span><strong>Không gian cá nhân</strong><small>{key ? 'Đã nhập key · chưa xác thực' : 'Chưa kết nối DeepSeek'}</small></span><span>⚙</span></button>
      </div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb">Không gian cá nhân <span>/</span><strong>{{ chat: 'Trò chuyện', memory: 'Bộ nhớ', knowledge: 'Kiến thức & chat mẫu', settings: 'Kết nối' }[page]}</strong></div><button className={`connection ${key ? 'has-key' : ''}`} onClick={() => setPage('settings')}><span className="status-dot"/>{key ? 'Đã nhập API key' : 'Kết nối DeepSeek'} ↗</button></header>
      {page === 'chat' ? <>
        <div className="chat-toolbar"><label className="model-picker"><span className="mini-mark">✳</span><select aria-label="Model DeepSeek" value={model} disabled={busy} onChange={e => setModel(e.target.value)}><option value="deepseek-flash">DeepSeek Flash</option><option value="deepseek-v4-pro">DeepSeek V4 Pro</option></select></label><label className="remember-toggle"><input type="checkbox" checked={remember} disabled={busy} onChange={e => setRemember(e.target.checked)}/><span>Tự ghi nhớ</span></label></div>
        {loading ? <div className="loading" role="status">Đang tải cuộc trò chuyện…</div> : <Chat key={cid} messages={messages} busy={busy} disabled={busy} onSend={send} error={error} reply={reply} connected={Boolean(key.trim())} onConnect={() => setPage('settings')} failedText={failedText}/>}
      </> : <div className="page-content">
        {error && <div className="error" role="alert">{error}</div>}
        {page === 'settings' && <><span className="eyebrow">KẾT NỐI CỦA BẠN</span><h1>Một chiếc chìa khóa.<br/><em>Bắt đầu cuộc trò chuyện.</em></h1><p className="page-intro">Dùng tài khoản DeepSeek của bạn. Chi phí được tính trên tài khoản API đó.</p><div className="settings-card"><label htmlFor="api-key">DeepSeek API key</label><input id="api-key" type="password" autoComplete="off" spellCheck={false} value={key} onChange={e => setKey(e.target.value)} placeholder="sk-…" maxLength={256}/><p>Key chỉ ở trong bộ nhớ của trang này, không lưu vào file hay trình duyệt. Tải lại trang sẽ cần nhập lại.</p><div className="button-row"><button className="primary" onClick={() => { setError(''); setPage('chat'); }} disabled={!key.trim()}>Bắt đầu chat ↗</button><button className="plain" onClick={() => setKey('')}>Xóa key</button></div></div><div className="info-line">↗ Tin nhắn, bộ nhớ và trích đoạn tài liệu liên quan được gửi đến DeepSeek khi chat. Bản local dùng cho một người trên máy này.</div></>}
        {page === 'memory' && <><span className="eyebrow">ĐƯỢC HỌC TỪ BẠN</span><h1>Những điều<br/><em>Aster ghi nhớ.</em></h1><p className="page-intro">Nói “từ giờ hãy…”, “thay đổi lại…” hoặc “quên điều đó đi” ngay trong chat. Bộ nhớ được lưu trên máy, qua các cuộc trò chuyện và lần khởi động.</p><div className="teaching-example"><span>THỬ NÓI</span>“Từ giờ tư vấn cho tôi thì hỏi nhu cầu trước, trả lời ngắn gọn.”<button onClick={() => setPage('chat')}>Dạy qua chat ↗</button></div><div className="memory-list">{state.memories.length ? state.memories.map(item => <article className="memory-item" key={item.id}><span className="tag">{labels[item.kind] || item.kind}</span><p>{item.content}</p><button disabled={busy} className="delete" onClick={() => remove('/memories/' + item.id)} aria-label={'Quên: ' + item.content}>Quên ×</button></article>) : <div className="empty-state"><span>✧</span><h2>Một khởi đầu mới.</h2><p>Chưa có điều gì được ghi nhớ. Hãy kể một chút về bạn.</p></div>}</div></>}
        {page === 'knowledge' && <><span className="eyebrow">TÀI LIỆU & PHONG CÁCH</span><h1>Cho Aster<br/><em>thêm chất liệu.</em></h1><p className="page-intro">Thêm kiến thức để tham khảo hoặc đoạn hội thoại tốt để học cách trả lời. Bản này nhận văn bản và file TXT, Markdown, CSV, JSON (UTF-8).</p><form className="knowledge-form" onSubmit={saveKnowledge}><div className="form-grid"><label>Tên nội dung<input required maxLength={120} placeholder="Ví dụ: Hướng dẫn tư vấn của tôi" value={title} onChange={e => setTitle(e.target.value)}/></label><label>Loại nội dung<select value={kind} onChange={e => setKind(e.target.value)}><option value="document">Tài liệu kiến thức</option><option value="example">Hội thoại mẫu</option></select></label></div><label>Nội dung<textarea required maxLength={200000} rows={7} placeholder="Dán tài liệu, hoặc hội thoại dạng Người dùng: … / Trợ lý: …" value={content} onChange={e => setContent(e.target.value)}/></label><div className="button-row"><label className="file-button">↥ Chọn file văn bản<input type="file" accept=".txt,.md,.csv,.json" onChange={async e => { const file = e.target.files?.[0]; if (!file) return; if (file.size > 200000) { setError('File tối đa 200 KB.'); return; } try { const text = await file.text(); if (text.includes('\u0000')) throw new Error('Cần file văn bản UTF-8.'); setContent(text); if (!title) setTitle(file.name.slice(0, 120)); } catch { setError('Không đọc được file văn bản.'); } }}/></label><button className="primary" disabled={knowledgeBusy}>{knowledgeBusy ? 'Đang lưu…' : 'Thêm vào kho ＋'}</button></div></form>{notice && <p className="saved-note" role="status">✓ {notice}</p>}<div className="knowledge-list">{state.knowledge.map(item => <article key={item.id}><span className="document-icon">▤</span><div><strong>{item.title}</strong><small>{item.kind === 'example' ? 'Chat mẫu' : 'Tài liệu'} · {item.size.toLocaleString()} ký tự</small></div><button className="delete" onClick={() => remove('/knowledge/' + item.id)}>Xóa ×</button></article>)}</div><p className="muted">Tìm tài liệu theo từ khóa không dấu; đưa tối đa 4 trích đoạn liên quan vào mỗi lượt chat. Chưa hỗ trợ PDF/Word hoặc tìm kiếm ngữ nghĩa.</p></>}
      </div>}
    </main>
  </div>;
}
