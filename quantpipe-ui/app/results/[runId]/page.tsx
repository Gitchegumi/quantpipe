"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBacktest } from "@/hooks/useBacktest";
import { ArrowDown, ArrowUp, Download, TrendingUp, Percent, Zap, AlertTriangle } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface Metrics {
  trade_count: number;
  win_rate: number;
  avg_r: number;
  sharpe_estimate: number | null;
  max_drawdown_r: number;
  max_drawdown_pct: number;
  profit_factor: number | null;
  total_return_pct: number;
}

interface Trade {
  signal_id: string;
  direction: string;
  open_timestamp: string;
  entry_fill_price: number;
  close_timestamp: string | null;
  exit_fill_price: number | null;
  exit_reason: string | null;
  pnl_r: number | null;
}

interface EquityPoint {
  timestamp: string;
  equity: number;
  drawdown_pct: number;
}

interface ResultData {
  run_id: string;
  pair: string;
  direction: string;
  metrics: Metrics;
  trades: Trade[];
  equity_curve: EquityPoint[];
}

function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  trend?: "up" | "down" | "neutral";
}) {
  const color =
    trend === "up" ? "text-emerald-400" : trend === "down" ? "text-rose-400" : "text-foreground";
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${color}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const runId = params.runId as string;
  const { getResults } = useBacktest();
  const [result, setResult] = useState<ResultData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getResults(runId)
      .then((data) => setResult(data))
      .finally(() => setLoading(false));
  }, [runId, getResults]);

  const m = result?.metrics;
  const winRate = m ? Math.round(m.win_rate * 100) : 0;
  const profitFactor = m?.profit_factor ? m.profit_factor.toFixed(2) : "—";
  const sharpe = m?.sharpe_estimate ? m.sharpe_estimate.toFixed(2) : "—";
  const maxDD = m ? `${(m.max_drawdown_pct * 100).toFixed(1)}%` : "—";
  const totalReturn = m ? `${m.total_return_pct.toFixed(2)}%` : "—";

  const chartData = useMemo(
    () =>
      result?.equity_curve.map((p) => ({
        time: p.timestamp ? new Date(p.timestamp).toLocaleDateString() : "",
        equity: p.equity,
      })) || [],
    [result]
  );

  const handleExport = (format: "json" | "csv") => {
    if (!result) return;
    if (format === "json") {
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${runId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const headers = ["signal_id", "direction", "open_timestamp", "entry_fill_price", "close_timestamp", "exit_fill_price", "exit_reason", "pnl_r"];
      const rows = result.trades.map((t) =>
        [t.signal_id, t.direction, t.open_timestamp, t.entry_fill_price, t.close_timestamp || "", t.exit_fill_price || "", t.exit_reason || "", t.pnl_r || ""].join(",")
      );
      const csv = [headers.join(","), ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${runId}_trades.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return <p className="text-muted-foreground">Loading results...</p>;
  }

  if (!result) {
    return <p className="text-muted-foreground">Result not found.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Backtest Results</h1>
          <p className="text-muted-foreground font-mono text-sm">{runId}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => handleExport("json")}>
            <Download className="mr-2 h-4 w-4" /> JSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport("csv")}>
            <Download className="mr-2 h-4 w-4" /> CSV
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <MetricCard label="Total Return" value={totalReturn} icon={TrendingUp} trend={m && m.total_return_pct >= 0 ? "up" : "down"} />
        <MetricCard label="Win Rate" value={`${winRate}%`} icon={Percent} trend={winRate >= 50 ? "up" : "down"} />
        <MetricCard label="Profit Factor" value={profitFactor} icon={Zap} />
        <MetricCard label="Max Drawdown" value={maxDD} icon={AlertTriangle} trend="down" />
        <MetricCard label="Sharpe" value={sharpe} icon={TrendingUp} />
      </div>

      {/* Equity Curve */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "0.5rem" }}
                />
                <Area type="monotone" dataKey="equity" stroke="#10b981" fillOpacity={1} fill="url(#equityGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground text-center py-8">No equity data available.</p>
          )}
        </CardContent>
      </Card>

      {/* Trade Table */}
      <Card>
        <CardHeader>
          <CardTitle>Trades ({result.trades.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-3">Direction</th>
                  <th className="text-left py-2 px-3">Entry</th>
                  <th className="text-left py-2 px-3">Exit</th>
                  <th className="text-left py-2 px-3">Reason</th>
                  <th className="text-right py-2 px-3">R:R</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.slice(0, 50).map((t, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-accent/50">
                    <td className="py-2 px-3">
                      <Badge variant={t.direction === "LONG" ? "default" : "destructive"}>
                        {t.direction === "LONG" ? <ArrowUp className="h-3 w-3 mr-1" /> : <ArrowDown className="h-3 w-3 mr-1" />}
                        {t.direction}
                      </Badge>
                    </td>
                    <td className="py-2 px-3">{t.entry_fill_price.toFixed(5)}</td>
                    <td className="py-2 px-3">{t.exit_fill_price?.toFixed(5) ?? "—"}</td>
                    <td className="py-2 px-3">{t.exit_reason ?? "—"}</td>
                    <td className={`py-2 px-3 text-right font-mono ${(t.pnl_r || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {t.pnl_r?.toFixed(2) ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
