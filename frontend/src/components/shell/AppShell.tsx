/**
 * AppShell — root layout: header + sidebar + main + statusbar.
 * Wraps all authenticated/app routes.
 */

import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from './AppHeader';
import { AppSidebar } from './AppSidebar';
import { AppStatusBar } from './AppStatusBar';
import { CommandPalette } from './CommandPalette';
import { useCommandPalette } from '../../context/CommandPaletteContext';

export const AppShell: React.FC = () => {
  const { open, close, isOpen } = useCommandPalette();

  // Global keyboard shortcut: Cmd/Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) close();
        else open();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, close, isOpen]);

  return (
    <div className="app-shell" data-testid="app-shell">
      <AppHeader />
      <AppSidebar />
      <main className="app-main" id="main-content" tabIndex={-1}>
        <Outlet />
      </main>
      <AppStatusBar />
      <CommandPalette />
    </div>
  );
};
