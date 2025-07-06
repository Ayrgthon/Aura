import { useState, useEffect } from 'react';

export interface SystemStats {
  cpu: number | null;
  gpu: number | null;
  ram: number | null;
  ssd: number | null;
}

export function useSystemStats() {
  const [stats, setStats] = useState<SystemStats>({ cpu: null, gpu: null, ram: null, ssd: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let interval: NodeJS.Timeout;

    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch('http://localhost:8000/system-stats');
        if (!res.ok) throw new Error('No se pudo obtener stats del sistema');
        const data = await res.json();
        if (isMounted) {
          setStats(data);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Error desconocido');
          setLoading(false);
        }
      }
    };

    fetchStats();
    interval = setInterval(fetchStats, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return { stats, loading, error };
} 