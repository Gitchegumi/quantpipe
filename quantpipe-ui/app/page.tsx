"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBacktest } from "@/hooks/useBacktest";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  ArrowRight,
} from "lucide-react";

interface RunSummary {
  run_id: string;
  status: string;
  strategy: string;
  pairs: string[];
  direction: string;
  start_time: string | null;
  end_time: string | null;
}

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "running"
      ? "running"
      : status === "completed"
      ? "completed"
      : status === "failed"
      ? "failed"
      : status === "cancelled"
      ? "cancelled"
      : "default";
  return <Badge variant={variant as any}>{status}</Badge>;
}

export default function DashboardPage() {
  const { listRuns } = useBacktest();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled) setRuns(data || []);
      })
      .finally(() => setLoading(false));
    return () => { cancelled = true; };
  }, [listRuns]);

  const completed = runs.filter((r) => r.status === "completed");
  const running = runs.filter((r) => r.status === "running");
  const failed = runs.filter((r) => r.status === "failed");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of backtest activity and performance.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runs.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">{completed.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <BarChart3 className="h-4 w-4 text-amber-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-400">{running.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <TrendingDown className="h-4 w-4 text-rose-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-rose-400">{failed.length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Backtest Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : runs.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">No backtest runs yet.</p>
              <Link href="/backtest">
                <Button>Start Your First Backtest <ArrowRight className="ml-2 h-4 w-4" /></Button>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3">Run ID</th>
                    <th className="text-left py-2 px-3">Status</th>
                    <th className="text-left py-2 px-3">Strategy</th>
                    <th className="text-left py-2 px-3">Pairs</th>
                    <th className="text-left py-2 px-3">Direction</th>
                    <th className="text-left py-2 px-3">Started</th>
                    <th className="text-right py-2 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 20).map((run) => (
                    <tr key={run.run_id} className="border-b border-border/50 hover:bg-accent/50">
                      <td className="py-2 px-3 font-mono text-xs">{run.run_id}</td>
                      <td className="py-2 px-3"><StatusBadge status={run.status} /></td>
                      <td className="py-2 px-3">{run.strategy}</td>
                      <td className="py-2 px-3">{run.pairs?.join(", ")}</td>
                      <td className="py-2 px-3">{run.direction}</td>
                      <td className="py-2 px-3 text-muted-foreground">
                        {run.start_time ? new Date(run.start_time).toLocaleString() : "—"}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <div className="flex gap-2 justify-end">
                          <Link href={`/monitor/${run.run_id}`}>
                            <Button variant="ghost" size="sm">Monitor</Button>
                          </Link>
                          {run.status === "completed" && (
                            <Link href={`/results/${run.run_id}`}>
                              <Button variant="ghost" size="sm">Results</Button>
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
