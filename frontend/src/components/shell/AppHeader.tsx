/**
 * AppHeader — top application bar.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { Command, Moon, Sun, Monitor, Aperture } from 'lucide-react';
import { IconButton } from '../ui/IconButton';
import { useTheme, type ThemePreference } from '../../context/ThemeContext';
import { useCommandPalette } from '../../context/CommandPaletteContext';
import { useHealthCheck } from '../../hooks/useHealthCheck';
import { StatusIndicator } from '../ui/StatusIndicator';

const THEME_CYCLE: ThemePreference[] = ['system', 'dark', 'light'];

function nextThemePref(current: ThemePreference): ThemePreference {
  const idx = THEME_CYCLE.indexOf(current);
  return THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
}

export const AppHeader: React.FC = () => {
  const { preference, setPreference } = useTheme();
  const { open, isOpen } = useCommandPalette();
  const { online } = useHealthCheck();

  const ThemeIcon =
    preference === 'dark'
      ? Moon
      : preference === 'light'
        ? Sun
        : Monitor;

  const themeLabel =
    preference === 'dark'
      ? 'Theme: dark (click to cycle)'
      : preference === 'light'
        ? 'Theme: light (click to cycle)'
        : 'Theme: system (click to cycle)';

  return (
    <header className="app-header" role="banner">
      {/* Brand */}
      <Link
        to="/"
        className="app-header__brand"
        aria-label="CodeLens AI — home"
      >
        <Aperture
          size={22}
          className="app-header__logo"
          aria-hidden="true"
          strokeWidth={1.5}
        />
        <span className="app-header__name">CodeLens AI</span>
      </Link>

      {/* Global search trigger */}
      <div className="app-header__center">
        <div className="search-input-wrap">
          <Command
            size={14}
            className="search-input-wrap__icon"
            aria-hidden="true"
          />
          <input
            className="search-input"
            placeholder="Search symbols, files, questions…"
            aria-label="Open command palette"
            readOnly
            onClick={open}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') open();
            }}
            role="button"
            aria-expanded={isOpen}
            aria-haspopup="dialog"
          />
          <div className="search-input__shortcut" aria-hidden="true">
            <kbd>⌘</kbd>
            <kbd>K</kbd>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="app-header__actions" role="toolbar" aria-label="Header actions">
        <StatusIndicator
          status={online === true ? 'online' : online === false ? 'offline' : 'pending'}
          label={online === true ? 'Backend online' : online === false ? 'Backend offline' : 'Connecting…'}
          showLabel={false}
        />
        <IconButton
          label={themeLabel}
          onClick={() => setPreference(nextThemePref(preference))}
        >
          <ThemeIcon size={16} aria-hidden="true" />
        </IconButton>
      </div>
    </header>
  );
};
