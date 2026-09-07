import React, { useState, useRef, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { MessageSquare, Send, Search, Code, Link as LinkIcon, FileCode2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { Badge } from '../components/ui/Badge';
import * as api from '../services/api';
import type { SearchResultItem } from '../types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  results?: SearchResultItem[];
  supportedClaims?: number;
  totalClaims?: number;
  intent?: string;
  isError?: boolean;
  statusText?: string;
}

// ---------------------------------------------------------------------------
// Markdown and Citation Parser component
// ---------------------------------------------------------------------------

interface ParsedMessageProps {
  text: string;
  results?: SearchResultItem[];
  repositoryId: string;
}

const MarkdownRenderer: React.FC<ParsedMessageProps> = ({ text, results = [], repositoryId }) => {
  // Very simplistic markdown + citation block parser
  const blocks = text.split(/(```[\s\S]*?```)/);
  
  return (
    <div className="markdown-body">
      {blocks.map((block, i) => {
        if (block.startsWith('```') && block.endsWith('```')) {
          const content = block.slice(3, -3);
          const firstNl = content.indexOf('\n');
          const lang = firstNl > -1 ? content.slice(0, firstNl).trim() : '';
          const code = firstNl > -1 ? content.slice(firstNl + 1) : content;
          return (
            <div key={i} className="code-block" data-lang={lang}>
              {lang && <div className="code-lang-label">{lang}</div>}
              <pre><code>{code}</code></pre>
            </div>
          );
        }

        // Parse paragraphs and citations within non-code blocks
        const paragraphs = block.split(/\n\n+/);
        return (
          <React.Fragment key={i}>
            {paragraphs.map((para, j) => {
              if (!para.trim()) return null;
              
              // Split by citation markers like [CTX:chunk-id]
              const citationParts = para.split(/(\[CTX:[^\]]+\])/);
              
              return (
                <p key={j}>
                  {citationParts.map((part, k) => {
                    const ctxMatch = part.match(/^\[CTX:([^\]]+)\]$/);
                    if (ctxMatch) {
                      const chunkId = ctxMatch[1];
                      const matchedResult = results.find(r => r.chunk_id === chunkId);
                      
                      // Identify index for tooltip or short label
                      const index = results.findIndex(r => r.chunk_id === chunkId) + 1;
                      
                      if (matchedResult) {
                        return (
                          <a 
                            key={k} 
                            href={`/symbols/${repositoryId}/${matchedResult.symbol_id}`} 
                            className="citation-badge"
                            title={`View ${matchedResult.symbol_name || matchedResult.file_path}`}
                            onClick={(e) => {
                              if (!matchedResult.symbol_id) {
                                e.preventDefault(); // If no symbol id, just keep as un-clickable marker
                              }
                            }}
                          >
                            [{index}]
                          </a>
                        );
                      }
                      
                      return <span key={k} className="citation-badge-unknown">[{chunkId}]</span>;
                    }

                    // Simple inline bolding
                    const boldParts = part.split(/(\*\*.*?\*\*)/);
                    return boldParts.map((bp, bpI) => {
                      if (bp.startsWith('**') && bp.endsWith('**')) {
                        return <strong key={bpI}>{bp.slice(2, -2)}</strong>;
                      }
                      // Simple inline code
                      const codeParts = bp.split(/(`.*?`)/);
                      return codeParts.map((cp, cpI) => {
                         if (cp.startsWith('`') && cp.endsWith('`')) {
                           return <code key={cpI} className="inline-code">{cp.slice(1, -1)}</code>;
                         }
                         return <React.Fragment key={cpI}>{cp}</React.Fragment>;
                      });
                    });
                  })}
                </p>
              );
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export const ChatPage: React.FC = () => {
  const { repositoryId } = useParams<{ repositoryId?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [inputVal, setInputVal] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const bottomRef = useRef<HTMLDivElement>(null);

  // If a symbol was provided, we pre-fill the query text as a helpful starting point,
  // but only once on mount.
  useEffect(() => {
    const symbolId = searchParams.get('symbol_id');
    if (symbolId && messages.length === 0 && !inputVal) {
      setInputVal(`Explain how the symbol ${symbolId} works.`);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  if (!repositoryId) {
    return (
      <div className="page-content" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <EmptyState
          title="Ask AI"
          description="Select a repository context to ask questions about the codebase."
          icon={<MessageSquare size={40} strokeWidth={1.5} />}
          action={<Button variant="primary" onClick={() => navigate('/repositories')} iconLeft={<Search size={16} />}>Select Repository</Button>}
        />
      </div>
    );
  }

  const handleSubmit = async () => {
    const query = inputVal.trim();
    if (!query) return;

    // Create user message
    const userMsg: Message = {
      id: Date.now().toString() + '-user',
      role: 'user',
      text: query,
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInputVal('');
    setIsLoading(true);

    try {
      const resp = await api.runQuery({
        query,
        repository_id: repositoryId,
        top_k: 10,
        generate_answer: true
      });

      const assistantMsg: Message = {
        id: Date.now().toString() + '-assistant',
        role: 'assistant',
        text: resp.answer?.answer_text || "I was unable to assemble enough context to answer this securely.",
        results: resp.results,
        supportedClaims: resp.answer?.supported_claims,
        totalClaims: resp.answer?.total_claims,
        intent: resp.answer?.intent,
        statusText: resp.answer?.overall_status,
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Unknown API error';
      const errorMsg: Message = {
        id: Date.now().toString() + '-error',
        role: 'assistant',
        text: `Error communicating with backend: ${errMsg}`,
        isError: true,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="page-content chat-layout" style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: '900px', margin: '0 auto', gap: 'var(--sp-4)' }}>
      <style>{`
        .chat-layout {
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        .chat-header {
          display: flex;
          align-items: center;
          gap: var(--sp-2);
          padding-bottom: var(--sp-2);
          border-bottom: 2px solid var(--border);
        }
        .chat-history {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--sp-6);
          overflow-y: auto;
          padding: var(--sp-2) 0;
        }
        .chat-message {
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
        }
        .chat-message.user {
           align-items: flex-end;
        }
        .chat-message.assistant {
           align-items: flex-start;
        }
        .chat-bubble {
          max-width: 85%;
          padding: var(--sp-3) var(--sp-4);
          border-radius: var(--radius-lg);
          font-size: var(--text-sm);
          line-height: 1.6;
        }
        .chat-bubble.user {
           background-color: var(--bg-overlay);
           color: var(--text-primary);
           border: 1px solid var(--border);
           border-bottom-right-radius: 4px;
        }
        .chat-bubble.assistant {
           background-color: transparent;
           color: var(--text-primary);
        }
        .chat-bubble.error {
           background-color: rgba(220, 38, 38, 0.1);
           border: 1px solid var(--error);
           color: var(--error);
        }
        
        .markdown-body p {
          margin-top: 0;
          margin-bottom: var(--sp-3);
        }
        .markdown-body p:last-child {
          margin-bottom: 0;
        }
        .inline-code {
          background-color: var(--bg-overlay);
          padding: 2px 4px;
          border-radius: 4px;
          font-family: var(--font-mono);
          font-size: 0.9em;
          border: 1px solid var(--border);
          color: var(--accent);
        }
        .code-block {
          background-color: var(--bg-overlay);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          margin-bottom: var(--sp-3);
          overflow: hidden;
        }
        .code-lang-label {
          background-color: var(--border);
          padding: 2px var(--sp-2);
          font-size: 11px;
          font-family: var(--font-mono);
          text-transform: uppercase;
          color: var(--text-secondary);
        }
        .code-block pre {
          margin: 0;
          padding: var(--sp-3);
          overflow-x: auto;
          font-family: var(--font-mono);
          font-size: 13px;
          line-height: 1.4;
        }
        .citation-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 10px;
          font-weight: 600;
          color: var(--bg-surface);
          background-color: var(--accent);
          border-radius: 9999px;
          padding: 0 4px;
          margin: 0 2px;
          text-decoration: none;
          vertical-align: super;
          transition: transform 0.1s;
        }
        .citation-badge:hover {
          transform: translateY(-1px);
        }
        .citation-badge-unknown {
          display: inline-flex;
          font-size: 10px;
          color: var(--text-secondary);
          background-color: var(--bg-overlay);
          border-radius: 4px;
          padding: 0 2px;
          margin: 0 2px;
        }
        
        .chat-sources {
          margin-top: var(--sp-4);
          padding: var(--sp-3);
          background-color: var(--bg-overlay);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
        }
        .chat-sources h4 {
           margin: 0;
           font-size: var(--text-xs);
           text-transform: uppercase;
           color: var(--text-muted);
        }
        .source-item {
          display: flex;
          align-items: center;
          gap: var(--sp-2);
          font-size: var(--text-sm);
        }
        .source-item .source-num {
          font-size: 10px;
          color: var(--text-secondary);
          background-color: var(--border);
          border-radius: 9999px;
          width: 16px;
          height: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        
        .chat-composer {
          display: flex;
          gap: var(--sp-2);
          align-items: flex-end;
          padding-top: var(--sp-2);
        }
        .chat-composer-input {
          flex: 1;
          min-height: 48px;
          max-height: 200px;
          padding: var(--sp-3);
          resize: none;
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          background-color: var(--bg-surface);
          color: var(--text-primary);
          font-family: inherit;
          font-size: var(--text-sm);
          line-height: 1.5;
          outline: none;
        }
        .chat-composer-input:focus {
          border-color: var(--accent);
          box-shadow: 0 0 0 1px var(--accent);
        }
      `}</style>
      
      <div className="chat-header">
        <MessageSquare size={20} className="text-accent" />
        <h2 className="text-lg font-semibold m-0">Ask AI</h2>
        <div style={{ marginLeft: 'auto' }}>
          <Badge variant="default" className="text-xs font-mono">{repositoryId}</Badge>
        </div>
      </div>

      <div className="chat-history">
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
             <MessageSquare size={48} opacity={0.2} style={{ margin: '0 auto var(--sp-4) auto' }} />
             <p className="text-lg font-medium mb-1">How can I help?</p>
             <p className="text-sm">Ask about symbols, authentication flows, or architecture.</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`chat-message ${msg.role}`}>
              <div className={`chat-bubble ${msg.role} ${msg.isError ? 'error' : ''}`}>
                {msg.role === 'user' ? (
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
                ) : (
                  <>
                    <MarkdownRenderer text={msg.text} results={msg.results} repositoryId={repositoryId} />
                    
                    {msg.statusText && (
                      <div style={{ marginTop: 'var(--sp-2)', display: 'flex', gap: 'var(--sp-2)' }}>
                        <Badge variant={msg.statusText === 'Fully Supported' ? 'success' : 'default'} className="text-xs">
                          {msg.statusText}
                        </Badge>
                        {msg.totalClaims !== undefined && msg.totalClaims > 0 && (
                          <Badge variant="default" className="text-xs">{msg.supportedClaims} / {msg.totalClaims} Claims Grounded</Badge>
                        )}
                      </div>
                    )}

                    {msg.results && msg.results.length > 0 && (
                      <div className="chat-sources">
                        <h4>Sources</h4>
                        {msg.results.slice(0, 5).map((r, i) => (
                           <div key={r.chunk_id} className="source-item">
                             <div className="source-num">{i + 1}</div>
                             <FileCode2 size={14} className="text-secondary" />
                             <span className="font-mono text-secondary" style={{ wordBreak: 'break-all' }}>
                               {r.file_path}
                             </span>
                             {r.start_line !== null && r.start_line !== undefined && (
                               <Badge variant="default" className="text-xs">{r.start_line}-{r.end_line}</Badge>
                             )}
                             {r.symbol_id && (
                               <a href={`/symbols/${repositoryId}/${r.symbol_id}`} style={{ marginLeft: 'auto', color: 'var(--text-secondary)' }}>
                                 <LinkIcon size={14} />
                               </a>
                             )}
                           </div>
                        ))}
                        {msg.results.length > 5 && (
                          <div className="text-xs text-muted" style={{ paddingLeft: '24px' }}>
                            + {msg.results.length - 5} additional sources
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="chat-message assistant">
            <div className="chat-bubble assistant text-muted" style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
              <Code size={16} className="animate-pulse" />
              <span>Analyzing the codebase...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-composer">
        <textarea
           className="chat-composer-input"
           placeholder="Ask a question about this codebase... (Enter to send, Shift+Enter for new line)"
           rows={1}
           value={inputVal}
           onChange={e => setInputVal(e.target.value)}
           onKeyDown={handleKeyDown}
           disabled={isLoading}
           aria-label="Message question to AI"
        />
        <Button 
          variant="primary" 
          onClick={handleSubmit} 
          disabled={isLoading || !inputVal.trim()}
          aria-label="Send message"
          style={{ height: '48px', width: '48px', padding: 0, justifyContent: 'center' }}
        >
          <Send size={18} />
        </Button>
      </div>

    </div>
  );
};
