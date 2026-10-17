import { Search, Menu, Github, Zap } from 'lucide-react';
import { repos, tabsByRepo } from '../data/navigation';

interface HeaderProps {
  activeRepo: string;
  activeTab: string;
  onRepoChange: (repoId: string) => void;
  onTabChange: (tabId: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onMenuToggle: () => void;
}

export default function Header({
  activeRepo, activeTab, onRepoChange, onTabChange,
  searchQuery, onSearchChange, onMenuToggle,
}: HeaderProps) {
  const currentTabs = tabsByRepo[activeRepo] ?? [];

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border)',
      flexShrink: 0,
    }}>

      {/* ── Row 1: Top bar ── */}
      <div style={{
        height: 'var(--header-height)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: 12,
      }}>
        {/* Mobile menu */}
        <button
          onClick={onMenuToggle}
          style={{
            display: 'none', padding: 8, background: 'none', border: 'none',
            color: 'var(--text-secondary)', cursor: 'pointer', borderRadius: 6,
          }}
          className="mobile-menu-btn"
        >
          <Menu size={18} />
        </button>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <div style={{
            width: 28, height: 28, background: 'var(--accent)', borderRadius: 6,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Zap size={16} color="white" />
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
            OpenHands
          </span>
          <span style={{
            background: 'var(--accent-bg)', border: '1px solid var(--accent-border)',
            color: 'var(--accent)', fontSize: 10, fontWeight: 600,
            padding: '2px 6px', borderRadius: 4, letterSpacing: '0.5px',
          }}>
            DOCS
          </span>
        </div>

        <div style={{ flex: 1 }} />

        {/* Search */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '6px 12px', width: 240, maxWidth: '100%',
        }}>
          <Search size={14} color="var(--text-muted)" />
          <input
            type="text" placeholder="Search docs..."
            value={searchQuery} onChange={e => onSearchChange(e.target.value)}
            style={{
              background: 'none', border: 'none', outline: 'none',
              color: 'var(--text-primary)', fontSize: 13, width: '100%',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <span style={{
            fontSize: 10, color: 'var(--text-muted)', background: 'var(--bg-hover)',
            padding: '1px 5px', borderRadius: 4, border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono)', flexShrink: 0,
          }}>⌘K</span>
        </div>

        {/* Version */}
        <span style={{
          fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-tertiary)',
          border: '1px solid var(--border)', padding: '4px 10px', borderRadius: 6,
          fontFamily: 'var(--font-mono)', flexShrink: 0,
        }}>v0.21.0</span>

        {/* GitHub */}
        <a href="https://github.com/All-Hands-AI/OpenHands" target="_blank" rel="noopener noreferrer"
          style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', padding: 6, borderRadius: 6 }}>
          <Github size={18} />
        </a>
      </div>

      {/* ── Row 2: Repo tab bar ── */}
      <div style={{
        height: 36,
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px 0 var(--sidebar-width)',
        gap: 4,
        borderTop: '1px solid var(--border)',
        background: 'var(--bg)',
      }}>
        {repos.map(repo => {
          const isActive = activeRepo === repo.id;
          return (
            <button
              key={repo.id}
              onClick={() => onRepoChange(repo.id)}
              style={{
                height: 26,
                padding: '0 12px',
                background: isActive ? 'var(--accent)' : 'transparent',
                border: isActive ? 'none' : '1px solid var(--border)',
                borderRadius: 6,
                color: isActive ? 'white' : 'var(--text-secondary)',
                fontWeight: isActive ? 600 : 400,
                fontSize: 12,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s',
                fontFamily: 'var(--font-sans)',
                letterSpacing: '0.1px',
              }}
            >
              {repo.title}
            </button>
          );
        })}
      </div>

      {/* ── Row 3: Sub-tab bar (filtered to active repo) ── */}
      <div style={{
        height: 'var(--tab-height)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 0 0 var(--sidebar-width)',
        gap: 2,
        overflowX: 'auto',
        overflowY: 'hidden',
      }} className="tab-bar">
        {currentTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              height: 'var(--tab-height)',
              padding: '0 14px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id
                ? '2px solid var(--accent)'
                : '2px solid transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: activeTab === tab.id ? 600 : 400,
              fontSize: 13,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s',
              fontFamily: 'var(--font-sans)',
              position: 'relative',
              top: 1,
            }}
          >
            {tab.title}
          </button>
        ))}
      </div>
    </div>
  );
}
