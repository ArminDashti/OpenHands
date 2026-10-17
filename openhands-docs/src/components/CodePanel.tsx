import { useState } from 'react';
import { Copy, Check, Play, ChevronDown } from 'lucide-react';
import type { PageContent } from '../data/pages';

interface CodePanelProps {
  page: PageContent;
}

function CodeBlock({ code, language, onCopy, copied }: {
  code: string;
  language: string;
  onCopy: () => void;
  copied: boolean;
}) {
  // Simple syntax highlighting via color classes
  const langColors: Record<string, string> = {
    bash: '#22c55e',
    python: '#3b82f6',
    json: '#f59e0b',
    yaml: '#8b5cf6',
    typescript: '#06b6d4',
    javascript: '#f59e0b',
    toml: '#ec4899',
  };

  const langColor = langColors[language] || '#a1a1aa';

  return (
    <div style={{
      background: '#0a0a0b',
      borderRadius: 8,
      overflow: 'hidden',
      border: '1px solid var(--border)',
    }}>
      {/* Code header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 14px',
        background: 'var(--bg-tertiary)',
        borderBottom: '1px solid var(--border)',
        gap: 8,
      }}>
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          color: langColor,
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.5px',
          textTransform: 'uppercase',
        }}>
          {language}
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={onCopy}
          style={{
            background: copied ? 'var(--green-bg)' : 'var(--bg-hover)',
            border: `1px solid ${copied ? 'rgba(34,197,94,0.3)' : 'var(--border)'}`,
            borderRadius: 5,
            padding: '3px 8px',
            color: copied ? 'var(--green)' : 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 11,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontFamily: 'var(--font-sans)',
            transition: 'all 0.15s',
          }}
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Code content */}
      <div style={{ overflowX: 'auto' }}>
        <pre style={{
          padding: '16px',
          margin: 0,
          fontSize: 12.5,
          lineHeight: 1.7,
          color: '#e5e7eb',
          fontFamily: 'var(--font-mono)',
          tabSize: 2,
        }}>
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}

function TryItOut({ tryItOut }: { tryItOut: NonNullable<PageContent['tryItOut']> }) {
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);

  const handleTry = () => {
    setIsLoading(true);
    // Simulate API response
    setTimeout(() => {
      const mockResponse = tryItOut.method === 'POST'
        ? JSON.stringify({
            id: 'conv_' + Math.random().toString(36).substr(2, 20),
            status: 'running',
            created_at: new Date().toISOString(),
            ...Object.fromEntries(
              (tryItOut.fields || [])
                .filter(f => fieldValues[f.name])
                .map(f => [f.name, fieldValues[f.name]])
            ),
          }, null, 2)
        : JSON.stringify({
            data: [],
            total: 0,
            page: 1,
          }, null, 2);
      setResponse(mockResponse);
      setIsLoading(false);
    }, 800);
  };

  return (
    <div style={{
      background: 'var(--bg-tertiary)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <Play size={13} color="var(--accent)" />
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
          Try It Out
        </span>
      </div>

      <div style={{ padding: 14 }}>
        {/* Endpoint */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 14,
          padding: '6px 10px',
          background: 'var(--bg)',
          borderRadius: 6,
          border: '1px solid var(--border)',
        }}>
          <span style={{
            fontSize: 11,
            fontWeight: 700,
            color: tryItOut.method === 'GET' ? 'var(--green)' : 'var(--accent)',
            fontFamily: 'var(--font-mono)',
            flexShrink: 0,
          }}>
            {tryItOut.method}
          </span>
          <span style={{
            fontSize: 12,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {tryItOut.endpoint}
          </span>
        </div>

        {/* Fields */}
        {tryItOut.fields && tryItOut.fields.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
            {tryItOut.fields.map(field => (
              <div key={field.name}>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: 5,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', textTransform: 'none', letterSpacing: 0 }}>
                    {field.name}
                  </span>
                  {field.required && (
                    <span style={{ color: 'var(--red)', fontSize: 10, fontWeight: 700 }}>required</span>
                  )}
                </label>
                <input
                  type="text"
                  placeholder={field.description}
                  value={fieldValues[field.name] || ''}
                  onChange={e => setFieldValues(v => ({ ...v, [field.name]: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    padding: '6px 10px',
                    color: 'var(--text-primary)',
                    fontSize: 12.5,
                    outline: 'none',
                    fontFamily: 'var(--font-sans)',
                    transition: 'border-color 0.15s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'var(--accent)'}
                  onBlur={e => e.target.style.borderColor = 'var(--border)'}
                />
              </div>
            ))}
          </div>
        )}

        {/* Send button */}
        <button
          onClick={handleTry}
          disabled={isLoading}
          style={{
            width: '100%',
            padding: '8px 16px',
            background: isLoading ? 'var(--bg-hover)' : 'var(--accent)',
            border: 'none',
            borderRadius: 6,
            color: isLoading ? 'var(--text-muted)' : 'white',
            fontSize: 13,
            fontWeight: 600,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            fontFamily: 'var(--font-sans)',
            transition: 'all 0.15s',
          }}
        >
          {isLoading ? (
            <>
              <div style={{
                width: 12,
                height: 12,
                border: '2px solid var(--text-muted)',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }} />
              Sending...
            </>
          ) : (
            <>
              <Play size={13} />
              Send Request
            </>
          )}
        </button>

        {/* Response */}
        {response && (
          <div style={{ marginTop: 12 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              marginBottom: 6,
            }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)' }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--green)' }}>200 OK</span>
            </div>
            <pre style={{
              background: '#0a0a0b',
              border: '1px solid var(--border)',
              borderRadius: 6,
              padding: 12,
              fontSize: 11.5,
              color: '#e5e7eb',
              overflowX: 'auto',
              fontFamily: 'var(--font-mono)',
              lineHeight: 1.6,
              margin: 0,
            }}>
              {response}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CodePanel({ page }: CodePanelProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const examples = page.codeExamples || [];

  const handleCopy = (code: string, index: number) => {
    navigator.clipboard.writeText(code).catch(() => {});
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (examples.length === 0 && !page.tryItOut) {
    return (
      <aside style={{
        width: 'var(--code-panel-width)',
        background: 'var(--bg-secondary)',
        borderLeft: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px',
          }}>
            <span style={{ fontSize: 20 }}>{'</>'}</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 12.5, lineHeight: 1.6 }}>
            Code examples will appear here
          </p>
        </div>
      </aside>
    );
  }

  return (
    <aside style={{
      width: 'var(--code-panel-width)',
      background: 'var(--bg-secondary)',
      borderLeft: '1px solid var(--border)',
      overflowY: 'auto',
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Panel header */}
      <div style={{
        padding: '14px 16px 12px',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.8px',
        }}>
          Code Examples
        </span>
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 16, flex: 1 }}>
        {/* Tab switcher for multiple examples */}
        {examples.length > 1 && (
          <div style={{
            display: 'flex',
            gap: 4,
            background: 'var(--bg-tertiary)',
            borderRadius: 8,
            padding: 3,
            border: '1px solid var(--border)',
          }}>
            {examples.map((ex, i) => (
              <button
                key={i}
                onClick={() => setActiveTab(i)}
                style={{
                  flex: 1,
                  padding: '5px 8px',
                  background: activeTab === i ? 'var(--bg-active)' : 'none',
                  border: 'none',
                  borderRadius: 5,
                  color: activeTab === i ? 'var(--text-primary)' : 'var(--text-muted)',
                  fontSize: 11.5,
                  fontWeight: activeTab === i ? 600 : 400,
                  cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {ex.label || ex.language}
              </button>
            ))}
          </div>
        )}

        {/* Code blocks */}
        {examples.length === 1 ? (
          <div>
            {examples[0].label && (
              <p style={{
                fontSize: 11.5,
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 8,
                letterSpacing: '0.3px',
              }}>
                {examples[0].label}
              </p>
            )}
            <CodeBlock
              code={examples[0].code}
              language={examples[0].language}
              onCopy={() => handleCopy(examples[0].code, 0)}
              copied={copiedIndex === 0}
            />
          </div>
        ) : examples.length > 1 ? (
          <CodeBlock
            code={examples[activeTab].code}
            language={examples[activeTab].language}
            onCopy={() => handleCopy(examples[activeTab].code, activeTab)}
            copied={copiedIndex === activeTab}
          />
        ) : null}

        {/* Try It Out */}
        {page.tryItOut && (
          <TryItOut tryItOut={page.tryItOut} />
        )}
      </div>

      {/* Spinner keyframes via style tag */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </aside>
  );
}
