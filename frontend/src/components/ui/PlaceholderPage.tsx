/**
 * PlaceholderPage — reusable shell for pages not yet implemented.
 * Used for routes reserved for 7A, 7B, 7C, 7D, 7E, 7F.
 */

import React from 'react';

interface PlaceholderPageProps {
  task: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  task,
  title,
  description,
  icon,
}) => {
  return (
    <div
      className="placeholder-page page-content"
      role="main"
      aria-label={title}
    >
      <span aria-hidden="true" style={{ fontSize: '2rem', color: 'var(--text-muted)' }}>
        {icon}
      </span>
      <span className="placeholder-page__label" aria-label={`Task ${task}`}>
        {task}
      </span>
      <h1 className="placeholder-page__title">{title}</h1>
      <p className="placeholder-page__desc">{description}</p>
    </div>
  );
};
