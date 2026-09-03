/**
 * CommandPalette — keyboard-driven navigation launcher.
 * Opens on Cmd/Ctrl+K.
 * Currently contains structural navigation actions only.
 * Full search (7F) is a separate task.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart2,
  FileCode2,
  GitBranch,
  MessageSquare,
  Network,
  Search,
  Layers,
} from 'lucide-react';
import { useCommandPalette } from '../../context/CommandPaletteContext';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  section: string;
  action: () => void;
  shortcut?: string[];
}

export const CommandPalette: React.FC = () => {
  const { isOpen, close } = useCommandPalette();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);

  const allCommands: CommandItem[] = [
    {
      id: 'nav-overview',
      section: 'Navigate',
      label: 'Overview',
      icon: <Layers size={16} />,
      action: () => { navigate('/overview'); close(); },
    },
    {
      id: 'nav-repositories',
      section: 'Navigate',
      label: 'Repositories',
      icon: <GitBranch size={16} />,
      action: () => { navigate('/repositories'); close(); },
    },
    {
      id: 'nav-search',
      section: 'Navigate',
      label: 'Search',
      icon: <Search size={16} />,
      action: () => { navigate('/search'); close(); },
    },
    {
      id: 'nav-symbols',
      section: 'Navigate',
      label: 'Symbols',
      icon: <FileCode2 size={16} />,
      action: () => { navigate('/symbols'); close(); },
    },
    {
      id: 'nav-graph',
      section: 'Navigate',
      label: 'Graph',
      icon: <Network size={16} />,
      action: () => { navigate('/graph'); close(); },
    },
    {
      id: 'nav-chat',
      section: 'Navigate',
      label: 'Chat',
      icon: <MessageSquare size={16} />,
      action: () => { navigate('/chat'); close(); },
    },
    {
      id: 'nav-impact',
      section: 'Navigate',
      label: 'Impact Analysis',
      icon: <BarChart2 size={16} />,
      action: () => { navigate('/impact'); close(); },
    },
  ];

  const filtered = query.trim()
    ? allCommands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          (c.description ?? '').toLowerCase().includes(query.toLowerCase()),
      )
    : allCommands;

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIdx(0);
  }, [query]);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isOpen]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        filtered[selectedIdx]?.action();
      } else if (e.key === 'Escape') {
        close();
      }
    },
    [filtered, selectedIdx, close],
  );

  if (!isOpen) return null;

  // Group by section
  const sections = [...new Set(filtered.map((c) => c.section))];

  return (
    <div
      className="cmd-overlay"
      onClick={close}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="cmd-palette"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Input */}
        <div className="cmd-palette__input-wrap">
          <Search size={16} className="cmd-palette__search-icon" aria-hidden="true" />
          <input
            ref={inputRef}
            className="cmd-palette__input"
            placeholder="Search commands and pages..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Command search"
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        {/* List */}
        <ul className="cmd-palette__list" role="listbox" aria-label="Commands">
          {filtered.length === 0 && (
            <li className="cmd-palette__section-label">No results</li>
          )}
          {sections.map((section) => (
            <React.Fragment key={section}>
              <li className="cmd-palette__section-label" role="presentation">
                {section}
              </li>
              {filtered
                .filter((c) => c.section === section)
                .map((cmd) => {
                  const idx = filtered.indexOf(cmd);
                  return (
                    <li
                      key={cmd.id}
                      role="option"
                      aria-selected={idx === selectedIdx}
                      className={`cmd-palette__item ${idx === selectedIdx ? 'cmd-palette__item--selected' : ''}`}
                      onClick={cmd.action}
                      onMouseEnter={() => setSelectedIdx(idx)}
                    >
                      <span className="cmd-palette__item-icon" aria-hidden="true">
                        {cmd.icon}
                      </span>
                      <span className="cmd-palette__item-label">{cmd.label}</span>
                    </li>
                  );
                })}
            </React.Fragment>
          ))}
        </ul>

        {/* Footer hints */}
        <div className="cmd-palette__footer" aria-hidden="true">
          <span className="cmd-palette__footer-hint">
            <kbd>↑↓</kbd> navigate
          </span>
          <span className="cmd-palette__footer-hint">
            <kbd>↵</kbd> open
          </span>
          <span className="cmd-palette__footer-hint">
            <kbd>Esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
};
