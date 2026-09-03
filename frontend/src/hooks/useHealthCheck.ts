import { useEffect, useState } from 'react';
import { fetchHealth } from '../services/api';

export interface HealthState {
  status: string;
  online: boolean | null;
}

export function useHealthCheck(): HealthState {
  const [status, setStatus] = useState<string>('checking...');
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((data) => {
        setStatus(data.status);
        setOnline(true);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setStatus('offline');
        setOnline(false);
      });

    return () => controller.abort();
  }, []);

  return { status, online };
}
