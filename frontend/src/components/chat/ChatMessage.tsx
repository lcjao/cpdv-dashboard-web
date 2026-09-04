import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { useState, useEffect } from 'react';

export interface Msg {
  role: 'user' | 'ai';
  text: string;
}

export default function ChatMessage({ msg }: { msg: Msg }) {
  const [html, setHtml] = useState(msg.text);
  useEffect(() => {
    if (msg.role === 'ai') {
      const raw = marked.parse(msg.text, { async: false }) as string;
      setHtml(DOMPurify.sanitize(raw));
    }
  }, [msg.text, msg.role]);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ color: msg.role === 'user' ? '#7db3ff' : '#8fe3b0', fontWeight: 700, marginBottom: 2 }}>
        {msg.role === 'user' ? '你' : 'AI'}
      </div>
      <div
        style={{ color: '#c9d4e5', lineHeight: 1.8 }}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
