"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text().catch(() => "Unknown error");
    throw new Error(`${res.status}: ${err}`);
  }
  return res.json();
}

export interface BacktestConfig {
  strategy: string;
  pairs: string[];
  direction: "LONG" | "SHORT" | "BOTH";
  dataset: "test" | "validate";
  timeframe: "1m" | "5m" | "15m" | "1h" | "4h" | "1d";
  simulation_type: "personal_capital" | "cti";
  starting_equity: number;
  max_risk_pct: number;
  sl_multiplier: number;
  tp_multiplier: number;
  dry_run: boolean;
  profiling: boolean;
  overrides?: Record<string, unknown>;
}

export function useBacktest() {
  const start = useCallback(async (config: BacktestConfig) => {
    const data = await apiFetch("/api/backtest", {
      method: "POST",
      body: JSON.stringify(config),
    });
    return data.runId as string;
  }, []);

  const getStatus = useCallback(async (runId: string) => {
    return apiFetch(`/api/backtest/${runId}`);
  }, []);

  const getResults = useCallback(async (runId: string) => {
    return apiFetch(`/api/backtest/${runId}/results`);
  }, []);

  const getLog = useCallback(async (runId: string) => {
    return apiFetch(`/api/backtest/${runId}/log`);
  }, []);

  const cancelRun = useCallback(async (runId: string) => {
    return apiFetch(`/api/backtest/${runId}`, { method: "DELETE" });
  }, []);

  const listRuns = useCallback(async () => {
    return apiFetch("/api/backtests");
  }, []);

  const listStrategies = useCallback(async () => {
    return apiFetch("/api/strategies") as Promise<
      { name: string; description: string; tags: string[] }[]
    >;
  }, []);

  const listPairs = useCallback(async () => {
    return apiFetch("/api/pairs") as Promise<string[]>;
  }, []);

  return {
    start,
    getStatus,
    getResults,
    getLog,
    cancelRun,
    listRuns,
    listStrategies,
    listPairs,
  };
}

export interface SseEvent {
  phase: string;
  current: number;
  total: number;
  percent: number;
  message: string;
  timestamp: string;
  metrics?: Record<string, unknown>;
}

export function useSse(url: string) {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<SseEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!url) return;

    const connect = () => {
      if (esRef.current) {
        esRef.current.close();
      }

      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setConnected(true);
        setError(null);
      };

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setEvents((prev) => [...prev, data]);
          setLastEvent(data);
          if (data.phase === "done" || data.phase === "failed" || data.phase === "cancelled") {
            es.close();
            setConnected(false);
          }
        } catch {
          // ignore parse errors
        }
      };

      es.addEventListener("heartbeat", () => {
        // keep alive
      });

      es.onerror = () => {
        setConnected(false);
        es.close();
        // Auto-reconnect after 2s unless run is done
        const last = lastEvent;
        if (!last || (last.phase !== "done" && last.phase !== "failed" && last.phase !== "cancelled")) {
          reconnectRef.current = setTimeout(connect, 2000);
        }
      };
    };

    connect();

    return () => {
      if (esRef.current) esRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [url, lastEvent?.phase]);

  return { connected, events, lastEvent, error };
}
