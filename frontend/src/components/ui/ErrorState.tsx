/**
 * ErrorState — contextual error message to display when a data fetch or sub-operation fails.
 */

import React from 'react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  action?: React.ReactNode;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'An error occurred',
  message,
  action,
}) => {
  return (
    <div className="error-state" role="alert">
      <h3 className="error-state__title">{title}</h3>
      <p className="error-state__message">{message}</p>
      {action && <div style={{ marginTop: 'var(--sp-2)' }}>{action}</div>}
    </div>
  );
};
