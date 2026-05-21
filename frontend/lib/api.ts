import {
  DatasetInfo,
  StrategyInfo,
  ScaffoldRequest,
  BacktestRequest,
  ProgressUpdate,
  BacktestResult,
} from "./types";

const API_BASE = "http://localhost:8000";

export const api = {
  /**
   * Fetch all currency pair datasets from the backend and adapt to the frontend schema.
   */
  async getDatasets(): Promise<DatasetInfo[]> {
    const response = await fetch(`${API_BASE}/datasets`);
    if (!response.ok) {
      throw new Error("Failed to fetch datasets");
    }
    const data = await response.json();
    const backendDatasets = data.datasets || [];
    return backendDatasets.map((d: any) => ({
      symbol: d.pair.toUpperCase(),
      test_available: !!d.test_path,
      validate_available: !!d.validate_path,
      test_rows: d.test_rows || undefined,
      validate_rows: d.validate_rows || undefined,
    }));
  },

  /**
   * Trigger ingest for a specific symbol dataset.
   */
  async triggerIngest(symbol: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/datasets/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, force: false }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to trigger ingest for ${symbol}`);
    }

    const data = await response.json();
    return {
      success: true,
      message: `Ingest job ${data.job_id} started for ${symbol}!`,
    };
  },

  /**
   * Fetch registered strategies.
   */
  async getStrategies(): Promise<StrategyInfo[]> {
    const response = await fetch(`${API_BASE}/strategies`);
    if (!response.ok) {
      throw new Error("Failed to fetch strategies");
    }
    const data = await response.json();
    const strategies = data.strategies || [];
    return strategies.map((s: any) => ({
      name: s.name,
      description: s.description || `${s.name} strategy`,
      version: s.version || "1.0.0",
      tags: s.tags || [],
    }));
  },

  /**
   * Scaffold a new strategy.
   */
  async scaffoldStrategy(form: ScaffoldRequest): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/strategies/scaffold`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.name,
        description: form.description,
        tags: [],
        auto_register: true,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "Failed to scaffold strategy");
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || "Failed to scaffold strategy");
    }

    return {
      success: true,
      message: `Scaffolded strategy '${data.name}' successfully under ${data.strategy_dir}!`,
    };
  },

  /**
   * Fetch all backtest results.
   */
  async getResults(): Promise<BacktestResult[]> {
    const response = await fetch(`${API_BASE}/results`);
    if (!response.ok) {
      throw new Error("Failed to fetch backtest results");
    }
    const data = await response.json();
    const backendResults = data.results || [];
    return backendResults.map((r: any) => ({
      job_id: r.run_id,
      run_id: r.run_id,
      pair: r.pair || "Unknown",
      strategy: r.strategy || "Unknown",
      direction: r.direction || "BOTH",
      dataset: r.dataset || "test",
      timeframe: r.timeframe || "1m",
      created_at: r.created_at || new Date().toISOString(),
      start_date: r.start_date,
      end_date: r.end_date,
      trades: r.trades || 0,
      win_rate: r.win_rate || 0,
      pnl: r.pnl || 0,
      expectancy: r.expectancy || 0,
      profit_factor: r.profit_factor || 0,
      max_drawdown: r.max_drawdown || 0,
      sharpe_est: r.sharpe_est || 0,
      average_r: r.average_r || 0,
    }));
  },

  /**
   * Submit a new backtest job, adapting frontend form schema to backend schema.
   */
  async submitBacktest(form: BacktestRequest): Promise<{ job_id: string; status: string }> {
    const backendRequest = {
      pair: form.pair,
      strategy: form.strategy,
      dataset: form.dataset,
      direction: form.direction,
      timeframe: form.timeframe,
      starting_balance: form.account_balance,
      risk_percent: form.risk_per_trade_pct,
      stop_policy: "ATR",
      reward_risk_ratio: form.target_r_mult,
      output_format: "json",
      dry_run: false,
      simulation_type: "Personal Capital",
      cti_mode: "2STEP",
    };

    const response = await fetch(`${API_BASE}/backtest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(backendRequest),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "Failed to submit backtest");
    }

    return await response.json();
  },

  /**
   * Subscribe to backtest progress using Server-Sent Events (SSE).
   */
  subscribeProgress(
    jobId: string,
    onProgress: (data: ProgressUpdate) => void,
    onError: (err: { message: string }) => void,
    onComplete: () => void
  ) {
    const url = `${API_BASE}/backtest/${jobId}/status`;
    const eventSource = new EventSource(url);

    const handleProgress = (event: MessageEvent) => {
      try {
        const raw = JSON.parse(event.data);
        const log = raw.log || "";
        const progress = raw.progress || 0;

        let current = progress;
        let total = 100;
        let phase = "Backtesting";
        let message = log || "Running backtest...";

        // Try to parse [current/total] from log
        const bracketMatch = /\[(\d+)\s*\/\s*(\d+)\]/.exec(log);
        if (bracketMatch) {
          current = parseInt(bracketMatch[1], 10);
          total = parseInt(bracketMatch[2], 10);
        } else {
          const slashMatch = /(\d+)\s*\/\s*(\d+)/.exec(log);
          if (slashMatch) {
            const cur = parseInt(slashMatch[1], 10);
            const tot = parseInt(slashMatch[2], 10);
            if (tot > 0 && tot <= 100000) {
              current = cur;
              total = tot;
            }
          }
        }

        // Try to extract phase if log starts with [Phase]
        const phaseMatch = /^\[([^\]]+)\]/.exec(log);
        if (phaseMatch) {
          phase = phaseMatch[1];
          message = log.substring(phaseMatch[0].length).trim();
        }

        onProgress({ phase, current, total, message });
      } catch (err) {
        console.error("Error parsing progress SSE event:", err);
      }
    };

    eventSource.addEventListener("progress", handleProgress);

    eventSource.addEventListener("complete", (event) => {
      handleProgress(event);
      eventSource.close();
      onComplete();
    });

    eventSource.addEventListener("error", (event) => {
      if (eventSource.readyState === EventSource.CLOSED) {
        onComplete();
      } else {
        onError({ message: "SSE stream connection error" });
        eventSource.close();
      }
    });

    eventSource.addEventListener("cancelled", () => {
      onError({ message: "Job was cancelled" });
      eventSource.close();
    });

    return {
      unsubscribe: () => {
        eventSource.close();
      },
    };
  },
};
