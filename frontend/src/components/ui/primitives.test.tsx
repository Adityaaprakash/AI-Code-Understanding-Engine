/**
 * UI primitive unit tests.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { IconButton } from '../ui/IconButton';
import { StatusIndicator } from '../ui/StatusIndicator';
import { EmptyState } from '../ui/EmptyState';
import { LoadingState } from '../ui/LoadingState';
import { ErrorState } from '../ui/ErrorState';

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('calls onClick handler', async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(<Button onClick={handler}>Click</Button>);
    await user.click(screen.getByRole('button'));
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('is disabled when loading', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows aria-busy when loading', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('is disabled when disabled prop is set', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies variant class', () => {
    render(<Button variant="primary">Primary</Button>);
    expect(screen.getByRole('button').className).toContain('btn--primary');
  });
});

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------

describe('Badge', () => {
  it('renders text', () => {
    render(<Badge>Indexed</Badge>);
    expect(screen.getByText('Indexed')).toBeInTheDocument();
  });

  it('applies variant class', () => {
    const { container } = render(<Badge variant="success">OK</Badge>);
    expect(container.querySelector('.badge--success')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// IconButton
// ---------------------------------------------------------------------------

describe('IconButton', () => {
  it('has accessible label', () => {
    render(<IconButton label="Close panel">✕</IconButton>);
    expect(screen.getByRole('button', { name: /close panel/i })).toBeInTheDocument();
  });

  it('calls onClick', async () => {
    const user = userEvent.setup();
    const fn = vi.fn();
    render(<IconButton label="Action" onClick={fn}>✕</IconButton>);
    await user.click(screen.getByRole('button'));
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// StatusIndicator
// ---------------------------------------------------------------------------

describe('StatusIndicator', () => {
  it('renders a status role element', () => {
    render(<StatusIndicator status="online" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders accessible label for indexed status', () => {
    render(<StatusIndicator status="indexed" />);
    const el = screen.getByRole('status');
    expect(el.getAttribute('aria-label')).toMatch(/indexed/i);
  });

  it('renders label text when showLabel is true', () => {
    render(<StatusIndicator status="indexed" showLabel />);
    expect(screen.getByText('indexed')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// EmptyState
// ---------------------------------------------------------------------------

describe('EmptyState', () => {
  it('renders the title', () => {
    render(<EmptyState title="No repositories" />);
    expect(screen.getByText('No repositories')).toBeInTheDocument();
  });

  it('renders the description', () => {
    render(
      <EmptyState
        title="No repositories"
        description="Connect a repository to get started."
      />,
    );
    expect(
      screen.getByText(/connect a repository/i),
    ).toBeInTheDocument();
  });

  it('has a region role with title as label', () => {
    render(<EmptyState title="Empty list" />);
    expect(screen.getByRole('region', { name: 'Empty list' })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// LoadingState
// ---------------------------------------------------------------------------

describe('LoadingState', () => {
  it('renders a default message', () => {
    render(<LoadingState />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders a custom message', () => {
    render(<LoadingState message="Fetching data" />);
    expect(screen.getByText('Fetching data')).toBeInTheDocument();
  });

  it('has accessible status role', () => {
    render(<LoadingState />);
    expect(screen.getByRole('status', { name: 'Loading content' })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ErrorState
// ---------------------------------------------------------------------------

describe('ErrorState', () => {
  it('renders a title and message', () => {
    render(<ErrorState title="Failed" message="Fetch error" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Fetch error')).toBeInTheDocument();
  });

  it('has an alert role', () => {
    render(<ErrorState message="Error" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
