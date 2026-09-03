import React from 'react';
import { Link } from 'react-router-dom';

export const NotFoundPage: React.FC = () => (
  <div
    className="placeholder-page page-content"
    role="main"
    aria-label="Page not found"
  >
    <span style={{ fontSize: '3rem', color: 'var(--text-muted)' }} aria-hidden="true">
      404
    </span>
    <h1 className="placeholder-page__title">Page not found</h1>
    <p className="placeholder-page__desc">
      The page you are looking for does not exist or has moved.
    </p>
    <Link to="/" className="btn btn--secondary">
      Go home
    </Link>
  </div>
);
