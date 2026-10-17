import { AlertCircle, CheckCircle, Info, AlertTriangle, ArrowRight } from 'lucide-react';
import type { PageContent, PageSection } from '../data/pages';

interface ContentAreaProps {
  page: PageContent;
  onPageChange: (route: string) => void;
}

function Callout({ variant = 'info', content }: { variant?: string; content?: string }) {
  const configs = {
    info: { icon: <Info size={15} />, bg: 'var(--blue-bg)', border: 'rgba(59,130,246,0.3)', color: 'var(--blue)' },
    success: { icon: <CheckCircle size={15} />, bg: 'var(--green-bg)', border: 'rgba(34,197,94,0.3)', color: 'var(--green)' },
    warning: { icon: <AlertTriangle size={15} />, bg: 'var(--yellow-bg)', border: 'rgba(234,179,8,0.3)', color: 'var(--yellow)' },
    danger: { icon: <AlertCircle size={15} />, bg: 'var(--red-bg)', border: 'rgba(239,68,68,0.3)', color: 'var(--red)' },
  };
  const cfg = configs[variant as keyof typeof configs] || configs.info;

  return (
    <div style={{
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      borderRadius: 8,
      padding: '12px 16px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: 10,
      margin: '12px 0',
    }}>
      <span style={{ color: cfg.color, marginTop: 1, flexShrink: 0 }}>{cfg.icon}</span>
      <p style={{ color: 'var(--text-primary)', fontSize: 13.5, lineHeight: 1.6, margin: 0 }}>{content}</p>
    </div>
  );
}

function Table({ headers, rows }: { headers?: string[]; rows?: string[][] }) {
  if (!headers || !rows) return null;
  return (
    <div style={{ overflowX: 'auto', margin: '16px 0' }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: 13,
      }}>
        <thead>
          <tr>
            {headers.map(h => (
              <th key={h} style={{
                textAlign: 'left',
                padding: '8px 12px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: 12,
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
                borderBottom: '1px solid var(--border)',
                whiteSpace: 'nowrap',
              }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
              {row.map((cell, j) => (
                <td key={j} style={{
                  padding: '8px 12px',
                  color: j === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontFamily: j === 0 ? 'var(--font-mono)' : 'var(--font-sans)',
                  fontSize: j === 0 ? 12.5 : 13,
                  background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                  verticalAlign: 'top',
                }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Steps({ steps }: { steps?: { title: string; content: string }[] }) {
  if (!steps) return null;
  return (
    <div style={{ margin: '16px 0', display: 'flex', flexDirection: 'column', gap: 0 }}>
      {steps.map((step, i) => (
        <div key={i} style={{ display: 'flex', gap: 16, position: 'relative' }}>
          {/* Step number and line */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'var(--accent)',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              fontWeight: 700,
              flexShrink: 0,
              zIndex: 1,
            }}>
              {i + 1}
            </div>
            {i < steps.length - 1 && (
              <div style={{
                width: 2,
                flex: 1,
                background: 'var(--border)',
                minHeight: 24,
              }} />
            )}
          </div>
          {/* Content */}
          <div style={{ paddingBottom: i < steps.length - 1 ? 20 : 0, paddingTop: 4 }}>
            <h4 style={{
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: 4,
            }}>
              {step.title}
            </h4>
            <p style={{
              fontSize: 13,
              color: 'var(--text-secondary)',
              lineHeight: 1.6,
              fontFamily: step.content.includes(' ') ? 'var(--font-sans)' : 'var(--font-mono)',
            }}>
              {step.content}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function Section({ section }: { section: PageSection }) {
  switch (section.type) {
    case 'heading':
      const HeadingTag = `h${section.level || 2}` as 'h1' | 'h2' | 'h3' | 'h4';
      const sizes = { 1: 28, 2: 21, 3: 17, 4: 15 };
      return (
        <HeadingTag style={{
          fontSize: sizes[section.level as keyof typeof sizes] || 20,
          fontWeight: section.level === 1 ? 800 : 700,
          color: 'var(--text-primary)',
          letterSpacing: section.level === 1 ? '-0.5px' : '-0.3px',
          marginTop: section.level === 2 ? 32 : section.level === 3 ? 24 : 16,
          marginBottom: 10,
          lineHeight: 1.3,
        }}>
          {section.content}
        </HeadingTag>
      );

    case 'paragraph':
      return (
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: 14,
          lineHeight: 1.75,
          margin: '8px 0 16px',
        }}>
          {section.content}
        </p>
      );

    case 'callout':
      return <Callout variant={section.variant} content={section.content} />;

    case 'table':
      return <Table headers={section.headers} rows={section.rows} />;

    case 'list':
      return (
        <ul style={{
          margin: '8px 0 16px',
          paddingLeft: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}>
          {(section.items || []).map((item, i) => (
            <li key={i} style={{
              color: 'var(--text-secondary)',
              fontSize: 13.5,
              lineHeight: 1.6,
            }}>
              {item}
            </li>
          ))}
        </ul>
      );

    case 'steps':
      return <Steps steps={section.steps} />;

    default:
      return null;
  }
}

export default function ContentArea({ page, onPageChange }: ContentAreaProps) {
  return (
    <main style={{
      flex: 1,
      overflowY: 'auto',
      padding: '32px 40px',
      minWidth: 0,
    }}>
      {/* Breadcrumb */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        marginBottom: 24,
        color: 'var(--text-muted)',
        fontSize: 12,
      }}>
        {page.route.split('/').filter(Boolean).map((segment, i, arr) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {i > 0 && <ArrowRight size={11} />}
            <span style={{
              color: i === arr.length - 1 ? 'var(--text-secondary)' : 'var(--text-muted)',
              textTransform: 'capitalize',
            }}>
              {segment.replace(/-/g, ' ')}
            </span>
          </span>
        ))}
      </div>

      {/* Page title */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{
          fontSize: 30,
          fontWeight: 800,
          color: 'var(--text-primary)',
          letterSpacing: '-0.7px',
          lineHeight: 1.2,
          marginBottom: 10,
        }}>
          {page.title}
        </h1>
        <p style={{
          fontSize: 15,
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          maxWidth: 600,
        }}>
          {page.description}
        </p>
      </div>

      {/* Divider */}
      <div style={{ borderBottom: '1px solid var(--border)', marginBottom: 28 }} />

      {/* Page sections */}
      <div style={{ maxWidth: 760 }}>
        {page.sections.map((section, i) => (
          <Section key={i} section={section} />
        ))}
      </div>

      {/* On this page quick nav */}
      {page.sections.filter(s => s.type === 'heading' && s.level === 2).length > 0 && (
        <div style={{
          position: 'fixed',
          right: 'var(--code-panel-width)',
          top: 120,
          width: 200,
          padding: '0 0 0 16px',
          borderLeft: '1px solid var(--border)',
          display: 'none',
        }} className="toc-panel">
          <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.8px', marginBottom: 10, textTransform: 'uppercase' }}>
            On this page
          </p>
          {page.sections
            .filter(s => s.type === 'heading' && s.level === 2)
            .map((s, i) => (
              <button
                key={i}
                style={{
                  display: 'block',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: 12.5,
                  cursor: 'pointer',
                  padding: '3px 0',
                  textAlign: 'left',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                {s.content}
              </button>
            ))
          }
        </div>
      )}

      {/* Footer */}
      <div style={{
        marginTop: 64,
        paddingTop: 24,
        borderTop: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <a
          href="https://github.com/All-Hands-AI/OpenHands"
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontSize: 12, color: 'var(--text-muted)', textDecoration: 'none' }}
        >
          Edit this page on GitHub ↗
        </a>
        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          OpenHands Documentation
        </p>
      </div>
    </main>
  );
}
