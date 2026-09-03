/**
 * AppSidebar — primary navigation sidebar.
 * Route-aware, keyboard accessible.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart2,
  FileCode2,
  GitBranch,
  Layers,
  MessageSquare,
  Network,
  Search,
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/overview',      label: 'Overview',        icon: <Layers size={16} /> },
  { to: '/repositories',  label: 'Repositories',    icon: <GitBranch size={16} /> },
  { to: '/search',        label: 'Search',          icon: <Search size={16} /> },
  { to: '/symbols',       label: 'Symbols',         icon: <FileCode2 size={16} /> },
  { to: '/graph',         label: 'Graph',           icon: <Network size={16} /> },
  { to: '/chat',          label: 'Chat',            icon: <MessageSquare size={16} /> },
  { to: '/impact',        label: 'Impact Analysis', icon: <BarChart2 size={16} /> },
];

export const AppSidebar: React.FC = () => {
  return (
    <nav
      className="app-sidebar"
      aria-label="Primary navigation"
    >
      <div className="sidebar-nav">
        <div className="sidebar-section">
          <span className="sidebar-section__label" aria-hidden="true">
            Explore
          </span>
          <ul role="list" style={{ listStyle: 'none' }}>
            {NAV_ITEMS.map((item) => (
              <li key={item.to} role="listitem">
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `sidebar-nav-item${isActive ? ' active' : ''}`
                  }
                  aria-label={item.label}
                  end={item.to === '/'}
                >
                  <span className="sidebar-nav-item__icon" aria-hidden="true">
                    {item.icon}
                  </span>
                  <span className="sidebar-nav-item__label">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </nav>
  );
};
