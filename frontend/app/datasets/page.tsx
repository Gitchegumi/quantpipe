"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { DatasetInfo } from "@/lib/types";
import { Database, RefreshCw, CheckCircle2, XCircle, BarChart3 } from "lucide-react";

const COMMON_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP", "GBPJPY"];

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState<Set<string>>(new Set());

  async function loadDatasets() {
    setLoading(true);
    try {
      const data = await api.getDatasets();
      setDatasets(data);
    } catch {
      // If API not ready, show all pairs with unknown status
      setDatasets(
        COMMON_PAIRS.map((symbol) => ({
          symbol,
          test_available: false,
          validate_available: false,
        }))
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  async function handleIngest(symbol: string) {
    setIngesting((prev) => new Set(prev).add(symbol));
    try {
      const result = await api.triggerIngest(symbol);
      toast.success(result.message || `Ingested ${symbol}`);
      await loadDatasets();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Failed to ingest ${symbol}`);
    } finally {
      setIngesting((prev) => {
        const next = new Set(prev);
        next.delete(symbol);
        return next;
      });
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Datasets</h1>
          <p className="text-muted-foreground">Manage currency pair datasets and ingestion</p>
        </div>
        <Button variant="outline" onClick={loadDatasets} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {loading
          ? Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-xl" />
            ))
          : datasets.map((ds) => (
              <Card key={ds.symbol} className="bg-card/50 backdrop-blur">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-lg font-mono">{ds.symbol}</CardTitle>
                  <div className="rounded-md bg-muted p-2">
                    <Database className="h-4 w-4 text-primary" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    {ds.test_available ? (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        <span className="text-muted-foreground">Test</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-muted-foreground/50" />
                        <span className="text-muted-foreground/50">Test</span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {ds.validate_available ? (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        <span className="text-muted-foreground">Validate</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-muted-foreground/50" />
                        <span className="text-muted-foreground/50">Validate</span>
                      </>
                    )}
                  </div>

                  {ds.test_rows && (
                    <div className="text-xs text-muted-foreground">
                      <BarChart3 className="inline h-3 w-3 mr-1" />
                      {ds.test_rows.toLocaleString()} test rows
                    </div>
                  )}

                  {!ds.test_available && !ds.validate_available && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => handleIngest(ds.symbol)}
                      disabled={ingesting.has(ds.symbol)}
                    >
                      {ingesting.has(ds.symbol) ? (
                        <RefreshCw className="mr-2 h-3 w-3 animate-spin" />
                      ) : (
                        <Database className="mr-2 h-3 w-3" />
                      )}
                      Ingest
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
      </div>
    </div>
  );
}
