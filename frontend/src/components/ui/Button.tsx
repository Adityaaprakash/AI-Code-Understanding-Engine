/**
 * Button — primary reusable button primitive.
 */

import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  loading = false,
  iconLeft,
  iconRight,
  children,
  disabled,
  className = '',
  ...rest
}) => {
  const sizeClass = size === 'sm' ? 'btn--sm' : size === 'lg' ? 'btn--lg' : '';

  return (
    <button
      className={`btn btn--${variant} ${sizeClass} ${className}`.trim()}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <span className="loading-spinner" aria-hidden="true" />
      ) : (
        iconLeft && <span className="btn__icon" aria-hidden="true">{iconLeft}</span>
      )}
      {children}
      {!loading && iconRight && (
        <span className="btn__icon" aria-hidden="true">{iconRight}</span>
      )}
    </button>
  );
};
