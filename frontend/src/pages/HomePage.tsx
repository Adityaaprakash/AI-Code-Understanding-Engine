import React from 'react';
import { Header } from '../components/Header';
import { useHealthCheck } from '../hooks/useHealthCheck';

export const HomePage: React.FC = () => {
  const { status, online } = useHealthCheck();

  return (
    <div className="container">
      <Header />
      <main className="main-content">
        <div className="card">
          <h2>System Status</h2>
          <div className="status-indicator">
            <span
              className={`status-dot ${online === true ? 'online' : online === false ? 'offline' : ''}`}
            ></span>
            <span className="status-text">Backend API: {status}</span>
          </div>
        </div>
      </main>
    </div>
  );
};
