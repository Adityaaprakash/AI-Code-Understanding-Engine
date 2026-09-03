/**
 * AppShell smoke tests — verifies the shell renders and navigation is accessible.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../../context/ThemeContext';
import { CommandPaletteProvider } from '../../context/CommandPaletteContext';
import { AppSidebar } from '../shell/AppSidebar';
import { AppHeader } from '../shell/AppHeader';
import { AppStatusBar } from '../shell/AppStatusBar';

// Mock the health check to avoid network calls
vi.mock('../../hooks/useHealthCheck', () => ({
  useHealthCheck: () => ({ status: 'ok', online: true }),
}));

function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <CommandPaletteProvider>
        <MemoryRouter initialEntries={['/overview']}>
          {children}
        </MemoryRouter>
      </CommandPaletteProvider>
    </ThemeProvider>
  );
}

// ---------------------------------------------------------------------------
// AppSidebar
// ---------------------------------------------------------------------------

describe('AppSidebar', () => {
  it('renders the primary navigation landmark', () => {
    render(<Providers><AppSidebar /></Providers>);
    expect(screen.getByRole('navigation', { name: /primary navigation/i })).toBeInTheDocument();
  });

  it('renders all expected navigation links', () => {
    render(<Providers><AppSidebar /></Providers>);
    const links = screen.getAllByRole('link');
    const labels = links.map((l) => l.getAttribute('aria-label'));
    expect(labels).toContain('Overview');
    expect(labels).toContain('Repositories');
    expect(labels).toContain('Search');
    expect(labels).toContain('Symbols');
    expect(labels).toContain('Graph');
    expect(labels).toContain('Chat');
    expect(labels).toContain('Impact Analysis');
  });

  it('marks the active route with active class', () => {
    render(
      <ThemeProvider>
        <CommandPaletteProvider>
          <MemoryRouter initialEntries={['/overview']}>
            <AppSidebar />
          </MemoryRouter>
        </CommandPaletteProvider>
      </ThemeProvider>,
    );
    const overviewLink = screen.getByRole('link', { name: /overview/i });
    expect(overviewLink.className).toContain('active');
  });

  it('nav links point to the correct paths', () => {
    render(<Providers><AppSidebar /></Providers>);
    expect(screen.getByRole('link', { name: /overview/i })).toHaveAttribute('href', '/overview');
    expect(screen.getByRole('link', { name: /repositories/i })).toHaveAttribute('href', '/repositories');
    expect(screen.getByRole('link', { name: /symbols/i })).toHaveAttribute('href', '/symbols');
    expect(screen.getByRole('link', { name: /graph/i })).toHaveAttribute('href', '/graph');
    expect(screen.getByRole('link', { name: /chat/i })).toHaveAttribute('href', '/chat');
    expect(screen.getByRole('link', { name: /impact analysis/i })).toHaveAttribute('href', '/impact');
  });
});

// ---------------------------------------------------------------------------
// AppHeader
// ---------------------------------------------------------------------------

describe('AppHeader', () => {
  it('renders the header banner landmark', () => {
    render(<Providers><AppHeader /></Providers>);
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders the CodeLens AI brand link', () => {
    render(<Providers><AppHeader /></Providers>);
    const brand = screen.getByRole('link', { name: /codelens ai/i });
    expect(brand).toBeInTheDocument();
  });

  it('renders the command palette trigger', () => {
    render(<Providers><AppHeader /></Providers>);
    const trigger = screen.getByRole('button', { name: /open command palette/i });
    expect(trigger).toBeInTheDocument();
  });

  it('theme toggle button has an accessible label', () => {
    render(<Providers><AppHeader /></Providers>);
    const themeBtn = screen.getByRole('button', { name: /theme/i });
    expect(themeBtn).toBeInTheDocument();
  });

  it('shows status indicator for backend', () => {
    render(<Providers><AppHeader /></Providers>);
    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// AppStatusBar
// ---------------------------------------------------------------------------

describe('AppStatusBar', () => {
  it('renders the status bar content info landmark', () => {
    render(<Providers><AppStatusBar /></Providers>);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('shows backend status text', () => {
    render(<Providers><AppStatusBar /></Providers>);
    expect(screen.getByText(/backend/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('applies data-theme attribute to html element', () => {
    render(
      <ThemeProvider>
        <div>hello</div>
      </ThemeProvider>,
    );
    // system preference resolves to dark in jsdom (no matchMedia)
    const val = document.documentElement.getAttribute('data-theme');
    expect(['dark', 'light']).toContain(val);
  });

  it('persists theme preference to localStorage', async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <CommandPaletteProvider>
          <MemoryRouter>
            <AppHeader />
          </MemoryRouter>
        </CommandPaletteProvider>
      </ThemeProvider>,
    );
    const themeBtn = screen.getByRole('button', { name: /theme/i });
    await user.click(themeBtn);
    const stored = localStorage.getItem('codelens-theme');
    expect(stored).toBeTruthy();
  });
});
