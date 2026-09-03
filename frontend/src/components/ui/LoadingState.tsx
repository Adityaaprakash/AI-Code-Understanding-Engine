/**
 * LoadingState — a generic full-area loading placeholder.
 */

import React from 'react';

export interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading...',
}) => {
  return (
    <div
      className="empty-state"
      role="status"
      aria-label="Loading content"
      aria-live="polite"
    >
      <div className="loading-spinner" aria-hidden="true" style={{ width: 32, height: 32, borderWidth: 3 }} />
      <p className="empty-state__title" style={{ marginTop: 'var(--sp-2)' }}>
        {message}
      </p>
    </div>
  );
};
