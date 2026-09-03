/**
 * AppStatusBar — bottom status bar showing backend connection,
 * indexing state, and system metadata.
 */

import React from 'react';
import { StatusIndicator } from '../ui/StatusIndicator';
import { useHealthCheck } from '../../hooks/useHealthCheck';

export const AppStatusBar: React.FC = () => {
  const { status, online } = useHealthCheck();

  const indicatorStatus =
    online === true ? 'online' : online === false ? 'offline' : 'pending';

  return (
    <footer
      className="app-statusbar"
      role="contentinfo"
      aria-label="Application status bar"
    >
      <div className="statusbar-item" aria-live="polite">
        <StatusIndicator status={indicatorStatus} />
        <span>
          {online === true
            ? `Backend ${status}`
            : online === false
              ? 'Backend offline'
              : 'Connecting…'}
        </span>
      </div>

      <div className="statusbar-divider" aria-hidden="true" />

      <div className="statusbar-item">
        <span>CodeLens AI</span>
      </div>

      <div className="statusbar-item statusbar-item--right">
        <span aria-label="Supported languages">Java · Python · TypeScript</span>
      </div>
    </footer>
  );
};
