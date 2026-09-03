/**
 * StatusIndicator — coloured dot conveying repository/connection status.
 */

import React from 'react';
import type { RepositoryStatus } from '../../types';

export type IndicatorStatus = RepositoryStatus | 'online' | 'offline' | 'unknown';

function dotModifier(status: IndicatorStatus): string {
  switch (status) {
    case 'indexed':
    case 'online':
      return 'status-dot--online';
    case 'indexing':
    case 'cloning':
    case 'pending':
      return 'status-dot--indexing';
    case 'error':
    case 'offline':
      return 'status-dot--error';
    default:
      return 'status-dot--pending';
  }
}

export interface StatusIndicatorProps {
  status: IndicatorStatus;
  label?: string;
  showLabel?: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  showLabel = false,
}) => {
  const displayLabel = label ?? status;

  return (
    <span
      role="status"
      aria-label={`Status: ${displayLabel}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--sp-2)' }}
    >
      <span className={`status-dot ${dotModifier(status)}`} aria-hidden="true" />
      {showLabel && (
        <span className="text-xs text-secondary">{displayLabel}</span>
      )}
    </span>
  );
};
