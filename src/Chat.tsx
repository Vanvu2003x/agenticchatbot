import { AssistantRuntimeProvider, ComposerPrimitive, MessagePrimitive, ThreadPrimitive, useExternalStoreRuntime, type AppendMessage, type TextMessagePartProps } from '@assistant-ui/react';
import Markdown from 'react-markdown';
import type { Message, Reply } from './api';

function Text({ text }: TextMessagePartProps) {
  return <Markdown>{text}</Markdown>;
}

function UserMessage() {
  return <MessagePrimitive.Root className="message user-message"><span className="message-label">BẠN</span><div className="bubble"><MessagePrimitive.Parts components={{ Text }} /></div></MessagePrimitive.Root>;
}

function AssistantMessage() {
  return <MessagePrimitive.Root className="message assistant-message"><span className="message-label"><span className="mini-mark">✳</span> ASTER</span><div className="prose"><MessagePrimitive.Parts components={{ Text }} /></div></MessagePrimitive.Root>;
}

type Props = {
  messages: Message[]; busy: boolean; disabled: boolean; onSend: (text: string) => Promise<void>;
  error: string; reply: Reply | null; onConnect: () => void; connected: boolean;
  failedText: string;
};

export default function Chat({ messages, busy, disabled, onSend, error, reply, onConnect, connected, failedText }: Props) {
  const runtime = useExternalStoreRuntime<Message>({
    messages, isRunning: busy, isSendDisabled: disabled,
    convertMessage: (message, idx) => ({ id: String(idx), role: message.role, content: [{ type: 'text', text: message.content }] }),
    onNew: async (message: AppendMessage) => {
      const text = message.content.filter(part => part.type === 'text').map(part => part.text).join('\n');
      if (text.trim()) await onSend(text);
    },
  });

  return <AssistantRuntimeProvider runtime={runtime}>
    <ThreadPrimitive.Root className="thread">
      <ThreadPrimitive.Viewport className="thread-viewport">
        <ThreadPrimitive.Empty>
          <div className="welcome">
            <span className="eyebrow"><span className="status-dot"/> KHÔNG GIAN CỦA BẠN</span>
            <div className="welcome-mark" aria-hidden="true">✳</div>
            <h1>Mỗi cuộc trò chuyện,<br/><em>hiểu bạn hơn một chút.</em></h1>
            <p>Cứ nói điều bạn đang nghĩ. Dạy mình cách bạn muốn được hỗ trợ,<br className="desktop-break"/> mình sẽ ghi nhớ cho những lần sau.</p>
            <div className="suggestions">
              {[
                ['01', 'Dạy mình cách trả lời', 'Từ giờ hãy trả lời ngắn gọn, bằng tiếng Việt. Nếu thiếu thông tin quan trọng thì hỏi lại trước.'],
                ['02', 'Ghi nhớ về bạn', 'Hãy nhớ rằng tôi đang xây dựng một chatbot dùng DeepSeek cho dự án cá nhân.'],
                ['03', 'Cùng giải quyết một việc', 'Giúp tôi lên kế hoạch cho một ngày làm việc tập trung.'],
              ].map(([number, title, prompt]) => <ThreadPrimitive.Suggestion key={number} prompt={prompt} autoSend={false} className="suggestion"><span>{number}</span><strong>{title}</strong><span aria-hidden="true">↗</span></ThreadPrimitive.Suggestion>)}
            </div>
          </div>
        </ThreadPrimitive.Empty>
        <div className="message-list"><ThreadPrimitive.Messages components={{ UserMessage, AssistantMessage }}/>
          {busy && <div className="thinking" role="status"><span className="mini-mark">✳</span> Đang đọc, ghi nhớ và trả lời<span className="dots">…</span></div>}
          {reply?.changes?.length ? <div className="saved-note" role="status">{reply.changes.map((change, index) => <div key={index}>✓ {change.action === 'deleted' ? 'Đã quên' : change.action === 'updated' ? 'Đã cập nhật' : 'Đã nhớ'}: {change.content}</div>)}</div> : null}
          {reply?.sources?.length ? <div className="sources">Tài liệu được đưa vào ngữ cảnh: {[...new Set(reply.sources.map(source => source.title))].join(' · ')}</div> : null}
          {reply?.warning && <p className="warning" role="status">{reply.warning}</p>}
        </div>
      </ThreadPrimitive.Viewport>
      <div className="composer-area">
        {error && <div role="alert" className="error">{error}{failedText && <button className="retry" disabled={busy} onClick={() => onSend(failedText)}>Gửi lại tin nhắn ↻</button>}</div>}
        {!connected && <button className="connect-hint" onClick={onConnect}>↗ Nhập DeepSeek API key để bắt đầu trò chuyện</button>}
        <ComposerPrimitive.Root className="composer">
          <ComposerPrimitive.Input aria-label="Tin nhắn" placeholder="Nhắn cho Aster, hoặc nói ‘hãy nhớ rằng…’" rows={2} maxLength={12000} className="composer-input"/>
          <div className="composer-bottom"><span><span className="small-spark">✳</span> Một trợ lý, có trí nhớ.</span><ComposerPrimitive.Send className="send-button" aria-label="Gửi tin nhắn">↑</ComposerPrimitive.Send></div>
        </ComposerPrimitive.Root>
        <p className="composer-footnote">Enter để gửi · Shift + Enter xuống dòng · AI có thể mắc lỗi, hãy kiểm tra thông tin quan trọng.</p>
      </div>
    </ThreadPrimitive.Root>
  </AssistantRuntimeProvider>;
}
