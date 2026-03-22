import { useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface BreadcrumbItem {
  label: string;
  path: string;
}

const BREADCRUMB_MAP: Record<string, BreadcrumbItem[]> = {
  '/': [{ label: 'nav.overview', path: '/' }],
  '/dashboard': [{ label: 'nav.dashboard', path: '/dashboard' }],
  '/experiments': [{ label: 'nav.experiments', path: '/experiments' }],
  '/optimization': [{ label: 'nav.optimization', path: '/optimization' }],
  '/chat': [{ label: 'nav.chat', path: '/chat' }],
  '/diagnostics': [{ label: 'nav.diagnostics', path: '/diagnostics' }],
  '/agents': [{ label: 'nav.agents', path: '/agents' }],
  '/knowledge': [{ label: 'nav.knowledge', path: '/knowledge' }],
  '/templates': [{ label: 'nav.templates', path: '/templates' }],
  '/settings': [{ label: 'nav.settings', path: '/settings' }],
};

export function Breadcrumb() {
  const { pathname } = useLocation();
  const { t } = useTranslation();

  // Extract breadcrumb from path
  let items: BreadcrumbItem[] = BREADCRUMB_MAP[pathname] || [];

  // Handle nested routes like /experiments/:id
  if (pathname.startsWith('/experiments/') && pathname !== '/experiments') {
    const expId = pathname.split('/')[2];
    items = [
      { label: 'nav.experiments', path: '/experiments' },
      { label: `Exp: ${expId}`, path: pathname },
    ];
  }

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 text-sm text-slate-600">
      {items.map((item, idx) => (
        <div key={item.path} className="flex items-center gap-2">
          <span className="text-slate-700 font-medium">
            {item.label.includes('.') ? t(item.label) : item.label}
          </span>
          {idx < items.length - 1 && (
            <ChevronRight className="h-4 w-4 text-slate-400" />
          )}
        </div>
      ))}
    </div>
  );
}
