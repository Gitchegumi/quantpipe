export interface DatasetInfo {
  symbol: string;
  test_available: boolean;
  validate_available: boolean;
  test_rows?: number;
  validate_rows?: number;
}

export interface StrategyInfo {
  name: string;
  description?: string;
  version?: string;
  tags?: string[];
  module_path?: string;
  registered_at?: string | Date;
}

export interface ScaffoldRequest {
  name: string;
  description: string;
}

export interface BacktestRequest {
  pair: string;
  direction: "LONG" | "SHORT" | "BOTH";
  dataset: "test" | "validate";
  timeframe: string;
  strategy: string;
  account_balance: number;
  risk_per_trade_pct: number;
  atr_stop_mult: number;
  target_r_mult: number;
}

export interface ProgressUpdate {
  phase: string;
  current: number;
  total: number;
  message: string;
}

export interface BacktestResult {
  job_id: string;
  run_id: string;
  pair: string;
  strategy: string;
  direction: string;
  dataset: string;
  timeframe: string;
  created_at: string;
  start_date?: string;
  end_date?: string;
  trades: number;
  win_rate: number;
  pnl: number;
  expectancy: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_est: number;
  average_r: number;
}
