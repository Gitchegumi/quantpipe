"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBacktest, useSse } from "@/hooks/useBacktest";
import { Activity, ArrowRight, RotateCcw, XCircle } from "lucide-react";

export default function MonitorPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.runId as string;
  const { getStatus, cancelRun } = useBacktest();

  const [status, setStatus] = useState<{
    status: string;
    current_phase?: string;
    percent_complete?: number;
  } | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
  const streamUrl = `${apiBase}/api/backtest/${runId}/stream`;
  const { connected, events, lastEvent } = useSse(streamUrl);

  useEffect(() => {
    let iv: ReturnType<typeof setInterval>;
    const poll = () => {
      getStatus(runId).then((s) => setStatus(s));
    };
    poll();
    iv = setInterval(poll, 3000);
    return () => clearInterval(iv);
  }, [runId, getStatus]);

  const progress = lastEvent?.percent ?? status?.percent_complete ?? 0;
  const phase = lastEvent?.phase ?? status?.current_phase ?? "pending";
  const isDone = phase === "done" || phase === "failed" || phase === "cancelled";

  const handleCancel = async () => {
    await cancelRun(runId);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Live Monitor</h1>
          <p className="text-muted-foreground font-mono text-sm">Run: {runId}</p>
        </div>
        <div className="flex items-center gap-2">
          {connected && !isDone && (
            <Badge variant="running">
              <Activity className="h-3 w-3 mr-1" /> Streaming
            </Badge>
          )}
          {!connected && !isDone && (
            <Badge variant="outline">Reconnecting...</Badge>
          )}
          {!isDone && (
            <Button variant="destructive" size="sm" onClick={handleCancel}>
              <XCircle className="h-4 w-4 mr-1" /> Cancel
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-4 w-4" /> Progress
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="capitalize">{phase}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} />
          </div>
          {lastEvent?.message && (
            <p className="text-sm text-muted-foreground">{lastEvent.message}</p>
          )}
          {isDone && (
            <div className="flex gap-3 pt-2">
              <Button onClick={() => router.push(`/results/${runId}`)}>
                View Results <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button variant="outline" onClick={() => router.push("/backtest")}>
                <RotateCcw className="mr-2 h-4 w-4" /> New Run
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Log</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-muted rounded-md p-3 h-64 overflow-auto font-mono text-xs space-y-1">
            {events.length === 0 ? (
              <p className="text-muted-foreground">Waiting for events...</p>
            ) : (
              events.slice(-100).map((e, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-muted-foreground shrink-0">
                    {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <span className="capitalize font-semibold text-primary">[{e.phase}]</span>
                  <span>{e.message}</span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
