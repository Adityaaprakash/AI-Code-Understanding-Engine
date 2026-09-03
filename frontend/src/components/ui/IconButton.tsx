/**
 * IconButton — icon-only button with accessible label.
 */

import React from 'react';

export interface IconButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Accessible label (required for icon-only buttons) */
  label: string;
  size?: 'sm' | 'md';
}

export const IconButton: React.FC<IconButtonProps> = ({
  label,
  size = 'md',
  children,
  className = '',
  ...rest
}) => {
  return (
    <button
      className={`icon-btn ${size === 'sm' ? 'icon-btn--sm' : ''} ${className}`.trim()}
      aria-label={label}
      title={label}
      {...rest}
    >
      {children}
    </button>
  );
};
