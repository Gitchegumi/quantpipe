"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { BacktestResult, DatasetInfo } from "@/lib/types";
import {
  Play,
  TrendingUp,
  TrendingDown,
  Activity,
  Database,
  ArrowRight,
  BarChart3,
  Zap,
} from "lucide-react";

function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
}: {
  title: string;
  value: string;
  description?: string;
  icon: React.ElementType;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <Card className="bg-card/50 backdrop-blur">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="rounded-md bg-muted p-2">
          <Icon className="h-4 w-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">
            {trend === "up" && <TrendingUp className="inline h-3 w-3 text-emerald-500 mr-1" />}
            {trend === "down" && <TrendingDown className="inline h-3 w-3 text-red-500 mr-1" />}
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [r, d] = await Promise.all([api.getResults(), api.getDatasets()]);
        setResults(r);
        setDatasets(d);
      } catch {
        // ignore for demo
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const bestStrategy = results.reduce(
    (best, r) => (r.pnl > (best?.pnl ?? -Infinity) ? r : best),
    null as BacktestResult | null
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Overview of your backtesting activity</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {loading ? (
          <>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </>
        ) : (
          <>
            <StatCard
              title="Total Backtests"
              value={results.length.toString()}
              description="All time runs"
              icon={BarChart3}
            />
            <StatCard
              title="Best Strategy"
              value={bestStrategy?.pair ?? "—"}
              description={`${bestStrategy ? `${bestStrategy.pnl >= 0 ? "+" : ""}${bestStrategy.pnl.toFixed(2)} PnL` : "No results yet"}`}
              icon={TrendingUp}
              trend={bestStrategy && bestStrategy.pnl >= 0 ? "up" : "down"}
            />
            <StatCard
              title="Win Rate Avg"
              value={`${results.length > 0 ? (results.reduce((s, r) => s + r.win_rate, 0) / results.length * 100).toFixed(1) : "0"}%`}
              description="Average across all runs"
              icon={Activity}
            />
            <StatCard
              title="Datasets Ready"
              value={datasets.length.toString()}
              description="Available pairs"
              icon={Database}
            />
          </>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/backtest">
          <Card className="group cursor-pointer bg-card/50 backdrop-blur transition-colors hover:bg-muted/50">
            <CardContent className="flex items-center gap-4 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <Play className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <div className="text-lg font-semibold">Run Backtest</div>
                <div className="text-sm text-muted-foreground">Execute a new backtest run</div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>

        <Link href="/datasets">
          <Card className="group cursor-pointer bg-card/50 backdrop-blur transition-colors hover:bg-muted/50">
            <CardContent className="flex items-center gap-4 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
                <Database className="h-5 w-5 text-emerald-500" />
              </div>
              <div className="flex-1">
                <div className="text-lg font-semibold">Build Dataset</div>
                <div className="text-sm text-muted-foreground">Ingest new price data</div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>

        <Link href="/results">
          <Card className="group cursor-pointer bg-card/50 backdrop-blur transition-colors hover:bg-muted/50">
            <CardContent className="flex items-center gap-4 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-500/10">
                <Zap className="h-5 w-5 text-purple-500" />
              </div>
              <div className="flex-1">
                <div className="text-lg font-semibold">View Results</div>
                <div className="text-sm text-muted-foreground">Analyze historical runs</div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Recent Runs */}
      <Card className="bg-card/50 backdrop-blur">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Runs</CardTitle>
          <Link href="/results" className="text-sm text-primary hover:underline">View all</Link>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <p className="text-sm text-muted-foreground">No backtest results yet. Run your first backtest to see results here.</p>
          ) : (
            <div className="space-y-2">
              {results.slice(0, 5).map((r) => (
                <div
                  key={r.job_id}
                  className="flex items-center justify-between rounded-lg border border-border px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={r.direction === "LONG" ? "default" : "secondary"}>
                      {r.direction}
                    </Badge>
                    <span className="font-mono text-sm font-medium">{r.pair}</span>
                    <Badge variant="outline">{r.dataset}</Badge>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className={`text-sm font-semibold ${r.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                        {r.pnl >= 0 ? "+" : ""}
                        {r.pnl.toFixed(2)}
                      </div>
                      <div className="text-xs text-muted-foreground">{(r.win_rate * 100).toFixed(1)}% WR · {r.trades} trades</div>
                    </div>
                    <Link
                      href={`/results/${r.job_id}`}
                      className="text-sm text-primary hover:underline"
                    >
                      Details
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
