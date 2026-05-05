"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatPercent, formatNumber, formatDate } from "@/lib/utils";
import type { BacktestResult } from "@/lib/types";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  ArrowRight,
  Calendar,
  Target,
} from "lucide-react";

function MetricCard({
  label,
  value,
  sub,
  positive,
}: {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean;
}) {
  return (
    <Card className="bg-card/50 backdrop-blur">
      <CardContent className="py-4">
        <div className="text-xs text-muted-foreground mb-1">{label}</div>
        <div className="text-xl font-bold">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
        {positive !== undefined && (
          <div className={`text-xs mt-1 ${positive ? "text-emerald-500" : "text-red-500"}`}>
            {positive ? "▲ Positive" : "▼ Negative"}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ResultsPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [selected, setSelected] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getResults();
        setResults(data);
      } catch {
        // ignore for demo
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Backtest Results</h1>
        <p className="text-muted-foreground">Review and compare historical backtest runs</p>
      </div>

      {selected ? (
        <div className="space-y-6">
          <button
            onClick={() => setSelected(null)}
            className="text-sm text-primary hover:underline"
          >
            ← Back to results list
          </button>

          <div className="flex items-center gap-3">
            <Badge variant="outline">{selected.pair}</Badge>
            <Badge variant={selected.direction === "LONG" ? "default" : "secondary"}>
              {selected.direction}
            </Badge>
            <Badge variant="outline">{selected.dataset}</Badge>
          </div>

          <div className="grid gap-4 md:grid-cols-5">
            <MetricCard
              label="Total Trades"
              value={selected.trades.toString()}
            />
            <MetricCard
              label="Win Rate"
              value={formatPercent(selected.win_rate)}
              sub={`${Math.round(selected.win_rate * selected.trades)} wins`}
              positive={selected.win_rate > 0.5}
            />
            <MetricCard
              label="Expectancy"
              value={selected.expectancy.toFixed(2) + "R"}
              sub="Avg R per trade"
              positive={selected.expectancy > 0}
            />
            <MetricCard
              label="Profit Factor"
              value={selected.profit_factor.toFixed(2)}
              sub="Gross wins / losses"
              positive={selected.profit_factor > 1}
            />
            <MetricCard
              label="Max Drawdown"
              value={`${(selected.max_drawdown * 100).toFixed(1)}%`}
              sub="Peak to trough"
              positive={selected.max_drawdown < 0.1}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="bg-card/50 backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">PnL Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${selected.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                  {selected.pnl >= 0 ? "+" : ""}
                  {selected.pnl.toFixed(2)}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  Sharpe est: {selected.sharpe_est.toFixed(2)} · Avg R: {selected.average_r.toFixed(2)}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur md:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Run Details</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Job ID</span>
                  <span className="font-mono">{selected.job_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created</span>
                  <span>{formatDate(selected.created_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Period</span>
                  <span>
                    {selected.start_date ? formatDate(selected.start_date) : "—"} →{" "}
                    {selected.end_date ? formatDate(selected.end_date) : "—"}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* TODO: Trade table + charts */}
          <Card className="bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle>Trade History</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Trade history table coming soon. Fetch via API:{" "}
                <code className="rounded bg-muted px-1 py-0.5">/api/results/{selected.job_id}/trades</code>
              </p>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="bg-card/50 backdrop-blur">
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {results.length === 0 ? (
                <div className="p-8 text-center">
                  <BarChart3 className="mx-auto h-10 w-10 text-muted-foreground/50 mb-3" />
                  <p className="text-muted-foreground">No backtest results yet.</p>
                  <Link href="/backtest" className="text-primary hover:underline text-sm">
                    Run your first backtest →
                  </Link>
                </div>
              ) : (
                results.map((r) => (
                  <button
                    key={r.job_id}
                    onClick={() => setSelected(r)}
                    className="flex w-full items-center justify-between px-6 py-4 transition-colors hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-3">
                      <Badge variant={r.direction === "LONG" ? "default" : "secondary"}>
                        {r.direction}
                      </Badge>
                      <span className="font-mono text-sm font-medium">{r.pair}</span>
                      <Badge variant="outline">{r.dataset}</Badge>
                      <span className="text-xs text-muted-foreground">
                        <Calendar className="inline h-3 w-3 mr-0.5" />
                        {formatDate(r.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className={`text-sm font-semibold ${r.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                          {r.pnl >= 0 ? "+" : ""}
                          {r.pnl.toFixed(2)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          <Target className="inline h-3 w-3 mr-0.5" />
                          {(r.win_rate * 100).toFixed(1)}% WR · {r.trades} trades
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
