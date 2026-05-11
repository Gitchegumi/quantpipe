"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useJobStore } from "@/lib/store";
import type { BacktestRequest, ProgressUpdate } from "@/lib/types";
import { Play, Loader2, Terminal } from "lucide-react";

const AVAILABLE_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP", "GBPJPY"];
const AVAILABLE_STRATEGIES = ["trend-pullback", "zscore-mean-reversion"];
const TIMEframes = ["1m", "5m", "15m", "1h", "4h", "1d"];

export default function BacktestPage() {
  const router = useRouter();
  const { job, progress, logs, isRunning, setJob, setProgress, addLog, clearLogs, setRunning } = useJobStore();

  const [form, setForm] = useState<BacktestRequest>({
    pair: "EURUSD",
    direction: "BOTH",
    dataset: "test",
    timeframe: "1m",
    strategy: "trend-pullback",
    account_balance: 10000,
    risk_per_trade_pct: 0.25,
    atr_stop_mult: 2.0,
    target_r_mult: 2.0,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isRunning) return;

    clearLogs();
    setRunning(true);
    setProgress(null);

    try {
      const response = await api.submitBacktest(form);
      setJob(response);
      addLog(`Job ${response.job_id} submitted`);

      // Start SSE for progress
      const sub = api.subscribeProgress(
        response.job_id,
        (data: ProgressUpdate) => {
          setProgress(data);
          addLog(`[${data.phase}] ${data.message}`);
        },
        (err) => {
          addLog(`Error: ${err.message}`);
          toast.error("Progress stream error");
        },
        () => {
          addLog("Stream complete");
          setRunning(false);
          toast.success("Backtest complete!");
          router.push(`/results/${response.job_id}`);
        }
      );

      // Store subscription for cleanup if needed
      (window as unknown as Record<string, unknown>).__qp_sse = sub;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit backtest");
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Run Backtest</h1>
        <p className="text-muted-foreground">Configure parameters and execute a backtest run</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-lg">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Currency Pair</Label>
                <Select
                  value={form.pair}
                  onValueChange={(v) => setForm((f) => ({ ...f, pair: v || f.pair }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_PAIRS.map((p) => (
                      <SelectItem key={p} value={p}>{p}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Direction</Label>
                <Select
                  value={form.direction}
                  onValueChange={(v) =>
                    setForm((f) => ({ ...f, direction: v as BacktestRequest["direction"] }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="LONG">LONG</SelectItem>
                    <SelectItem value="SHORT">SHORT</SelectItem>
                    <SelectItem value="BOTH">BOTH</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Dataset</Label>
                <Select
                  value={form.dataset}
                  onValueChange={(v) =>
                    setForm((f) => ({ ...f, dataset: v as "test" | "validate" }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="test">Test</SelectItem>
                    <SelectItem value="validate">Validate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Strategy</Label>
                <Select
                  value={form.strategy}
                  onValueChange={(v) => setForm((f) => ({ ...f, strategy: v || f.strategy }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_STRATEGIES.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Timeframe</Label>
                <Select
                  value={form.timeframe}
                  onValueChange={(v) => setForm((f) => ({ ...f, timeframe: v || f.timeframe }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEframes.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Account Balance</Label>
                <Input
                  type="number"
                  value={form.account_balance}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, account_balance: Number(e.target.value) }))
                  }
                />
              </div>
            </div>

            <Separator />

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Risk per Trade (%)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={form.risk_per_trade_pct}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, risk_per_trade_pct: Number(e.target.value) }))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label>ATR Stop Multiplier</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={form.atr_stop_mult}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, atr_stop_mult: Number(e.target.value) }))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label>Target R Multiple</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={form.target_r_mult}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, target_r_mult: Number(e.target.value) }))
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-4">
          <Button type="submit" disabled={isRunning} size="lg">
            {isRunning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running…
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Backtest
              </>
            )}
          </Button>

          {isRunning && (
            <Badge variant="secondary" className="self-center">
              {progress ? `${progress.phase}: ${progress.current}/${progress.total}` : "Starting…"}
            </Badge>
          )}
        </div>
      </form>

      {/* Progress */}
      {progress && (
        <Card className="bg-card/50 backdrop-blur">
          <CardContent className="space-y-3 py-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{progress.phase}</span>
              <span className="text-muted-foreground">
                {((progress.current / progress.total) * 100).toFixed(1)}%
              </span>
            </div>
            <Progress value={(progress.current / progress.total) * 100} />
            <p className="text-xs text-muted-foreground">{progress.message}</p>
          </CardContent>
        </Card>
      )}

      {/* Logs */}
      {logs.length > 0 && (
        <Card className="bg-card/50 backdrop-blur">
          <CardHeader className="flex flex-row items-center gap-2 pb-2">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">Execution Log</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-64 overflow-y-auto space-y-1 rounded-md bg-muted p-3 font-mono text-xs">
              {logs.map((log, i) => (
                <div key={i} className="text-muted-foreground">
                  <span className="text-muted-foreground/50 mr-2">{i + 1}</span>
                  {log}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
