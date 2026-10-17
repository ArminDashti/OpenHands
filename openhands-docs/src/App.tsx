import { useState, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ContentArea from './components/ContentArea';
import CodePanel from './components/CodePanel';
import { repos, tabsByRepo, navigationByTab } from './data/navigation';
import { getPage } from './data/pages';

export default function App() {
  const [activeRepo, setActiveRepo]   = useState('openhands');
  const [activeTab, setActiveTab]     = useState('introduction');
  const [activePage, setActivePage]   = useState('/');
  const [searchQuery, setSearchQuery] = useState('');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const handleRepoChange = useCallback((repoId: string) => {
    const repo = repos.find(r => r.id === repoId);
    if (!repo) return;
    setActiveRepo(repoId);
    const firstTab = tabsByRepo[repoId]?.[0];
    const tabId = firstTab?.id ?? repo.defaultTab;
    setActiveTab(tabId);
    const navItems = navigationByTab[tabId];
    if (navItems && navItems.length > 0) {
      setActivePage(navItems[0].route);
    } else if (firstTab) {
      setActivePage(firstTab.slug);
    }
  }, []);

  const handleTabChange = useCallback((tabId: string) => {
    setActiveTab(tabId);
    const allTabs = Object.values(tabsByRepo).flat();
    const tab = allTabs.find(t => t.id === tabId);
    if (tab) {
      const navItems = navigationByTab[tabId];
      if (navItems && navItems.length > 0) {
        setActivePage(navItems[0].route);
      } else {
        setActivePage(tab.slug);
      }
    }
  }, []);

  const handlePageChange = useCallback((route: string) => {
    setActivePage(route);
    setMobileSidebarOpen(false);
  }, []);

  const navItems   = navigationByTab[activeTab] || [];
  const currentPage = getPage(activePage);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>
      <Header
        activeRepo={activeRepo}
        activeTab={activeTab}
        onRepoChange={handleRepoChange}
        onTabChange={handleTabChange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onMenuToggle={() => setMobileSidebarOpen(!mobileSidebarOpen)}
      />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar
          navItems={navItems}
          activePage={activePage}
          onPageChange={handlePageChange}
          searchQuery={searchQuery}
          isOpen={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
        />
        <ContentArea page={currentPage} onPageChange={handlePageChange} />
        <CodePanel page={currentPage} />
      </div>
    </div>
  );
}
