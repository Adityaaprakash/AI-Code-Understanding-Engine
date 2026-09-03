/**
 * Panel — bordered surface container.
 */

import React from 'react';

export interface PanelProps {
  title?: string;
  elevated?: boolean;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const Panel: React.FC<PanelProps> = ({
  title,
  elevated = false,
  headerRight,
  children,
  className = '',
}) => {
  return (
    <section
      className={`panel ${elevated ? 'panel--elevated' : ''} ${className}`.trim()}
    >
      {title && (
        <div className="panel__header">
          <h2 className="panel__title">{title}</h2>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      <div className="panel__body">{children}</div>
    </section>
  );
};
