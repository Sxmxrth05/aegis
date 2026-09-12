import { NavLink } from 'react-router-dom';

import { useNegotiationStore, type ConnectionStatus } from '../../store/useNegotiationStore';

const links = [
  { to: '/monitor', label: 'Monitor' },
  { to: '/negotiate', label: 'Negotiate' },
  { to: '/history', label: 'History' },
  { to: '/about', label: 'About' },
];

const STATUS_DISPLAY: Record<ConnectionStatus, { label: string; dotClassName: string }> = {
  connecting: { label: 'Connecting', dotClassName: 'bg-warning shadow-[0_0_6px_var(--color-warning)]' },
  connected: { label: 'Live', dotClassName: 'bg-success shadow-[0_0_6px_var(--color-success)]' },
  reconnecting: {
    label: 'Reconnecting',
    dotClassName: 'bg-warning shadow-[0_0_6px_var(--color-warning)] animate-pulse',
  },
  disconnected: { label: 'Disconnected', dotClassName: 'bg-danger shadow-[0_0_6px_var(--color-danger)]' },
};

export function NavBar() {
  const connectionStatus = useNegotiationStore((s) => s.connectionStatus);
  const { label, dotClassName } = STATUS_DISPLAY[connectionStatus];

  return (
    <header className="h-16 border-b border-border bg-surface flex items-center justify-between px-8">
      <NavLink to="/" className="text-text-primary font-semibold tracking-tight">
        Aegis
      </NavLink>
      <nav className="flex items-center gap-6">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              isActive
                ? 'text-text-primary text-sm font-medium'
                : 'text-text-secondary text-sm hover:text-text-primary'
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="flex items-center gap-2 text-xs text-text-muted">
        <span className={`h-2 w-2 rounded-full ${dotClassName}`} />
        {label}
      </div>
    </header>
  );
}
