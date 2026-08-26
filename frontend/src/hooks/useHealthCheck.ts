import { useEffect, useState } from 'react';
import { fetchHealth } from '../services/api';

export function useHealthCheck() {
  const [status, setStatus] = useState<string>('checking...');
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setStatus(data.status);
        setOnline(true);
      })
      .catch(() => {
        setStatus('offline');
        setOnline(false);
      });
  }, []);

  return { status, online };
}
