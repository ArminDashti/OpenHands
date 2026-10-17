import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, X } from 'lucide-react';
import type { NavItem } from '../data/navigation';

interface SidebarProps {
  navItems: NavItem[];
  activePage: string;
  onPageChange: (route: string) => void;
  searchQuery: string;
  isOpen: boolean;
  onClose: () => void;
}

function NavItemComponent({
  item,
  activePage,
  onPageChange,
  depth = 0,
  searchQuery,
}: {
  item: NavItem;
  activePage: string;
  onPageChange: (route: string) => void;
  depth?: number;
  searchQuery: string;
}) {
  const hasChildren = item.children && item.children.length > 0;
  const isActive = activePage === item.route;
  const isChildActive = hasChildren && item.children!.some(c =>
    activePage === c.route || activePage.startsWith(c.route + '/')
  );

  const [isExpanded, setIsExpanded] = useState(isActive || isChildActive);

  useEffect(() => {
    if (isActive || isChildActive) {
      setIsExpanded(true);
    }
  }, [isActive, isChildActive]);

  const matches = searchQuery
    ? item.title.toLowerCase().includes(searchQuery.toLowerCase())
    : true;

  const childMatches = hasChildren && item.children!.some(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (searchQuery && !matches && !childMatches) return null;

  return (
    <div>
      <button
        onClick={() => {
          if (hasChildren) {
            setIsExpanded(!isExpanded);
          }
          onPageChange(item.route);
        }}
        style={{
          width: '100%',
          textAlign: 'left',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: `5px ${8 + depth * 12}px`,
          background: isActive ? 'var(--accent-bg)' : 'none',
          border: 'none',
          borderLeft: isActive
            ? '2px solid var(--accent)'
            : depth === 0 && isChildActive
              ? '2px solid var(--border-light)'
              : '2px solid transparent',
          color: isActive
            ? 'var(--accent)'
            : depth === 0
              ? 'var(--text-primary)'
              : 'var(--text-secondary)',
          fontSize: depth === 0 ? 13 : 12.5,
          fontWeight: depth === 0 ? 600 : isActive ? 500 : 400,
          cursor: 'pointer',
          borderRadius: '0 6px 6px 0',
          marginRight: 8,
          transition: 'all 0.1s',
          fontFamily: 'var(--font-sans)',
          lineHeight: 1.4,
        }}
        onMouseEnter={e => {
          if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
        }}
        onMouseLeave={e => {
          if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'none';
        }}
      >
        <span style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6 }}>
          {item.title}
          {item.badge && (
            <span style={{
              fontSize: 9,
              fontWeight: 700,
              padding: '1px 5px',
              background: 'var(--yellow-bg)',
              color: 'var(--yellow)',
              borderRadius: 4,
              letterSpacing: '0.5px',
              border: '1px solid rgba(234,179,8,0.2)',
            }}>
              {item.badge}
            </span>
          )}
          {item.isNew && (
            <span style={{
              fontSize: 9,
              fontWeight: 700,
              padding: '1px 5px',
              background: 'var(--green-bg)',
              color: 'var(--green)',
              borderRadius: 4,
              letterSpacing: '0.5px',
            }}>NEW</span>
          )}
        </span>
        {hasChildren && (
          <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
            {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        )}
      </button>

      {hasChildren && isExpanded && (
        <div>
          {item.children!.map(child => (
            <NavItemComponent
              key={child.id}
              item={child}
              activePage={activePage}
              onPageChange={onPageChange}
              depth={depth + 1}
              searchQuery={searchQuery}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sidebar({ navItems, activePage, onPageChange, searchQuery, isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            zIndex: 40,
            display: 'none',
          }}
          className="mobile-overlay"
        />
      )}

      <aside
        style={{
          width: 'var(--sidebar-width)',
          background: 'var(--bg-secondary)',
          borderRight: '1px solid var(--border)',
          overflowY: 'auto',
          flexShrink: 0,
          padding: '16px 0',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {/* Mobile close button */}
        <div style={{ padding: '0 12px 8px', display: 'none' }} className="mobile-close">
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: 4,
            }}
          >
            <X size={16} />
          </button>
        </div>

        {navItems.length === 0 ? (
          <div style={{ padding: '16px 16px', color: 'var(--text-muted)', fontSize: 13 }}>
            No pages available
          </div>
        ) : (
          navItems.map(item => (
            <NavItemComponent
              key={item.id}
              item={item}
              activePage={activePage}
              onPageChange={onPageChange}
              searchQuery={searchQuery}
            />
          ))
        )}
      </aside>
    </>
  );
}
