"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { StrategyInfo, ScaffoldRequest } from "@/lib/types";
import { Code2, Plus, Tag, FileCode2, RefreshCw } from "lucide-react";

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [scaffoldForm, setScaffoldForm] = useState<ScaffoldRequest>({
    name: "",
    description: "",
  });
  const [submitting, setSubmitting] = useState(false);

  async function loadStrategies() {
    setLoading(true);
    try {
      const data = await api.getStrategies();
      setStrategies(data);
    } catch {
      // Demo fallback
      setStrategies([
        {
          name: "trend-pullback",
          description: "Trend following with pullback entries on EMA alignment",
          version: "1.0.0",
          tags: ["trend", "ema", "pullback"],
        },
        {
          name: "zscore-mean-reversion",
          description: "Mean reversion using z-score thresholds",
          version: "1.0.0",
          tags: ["mean-reversion", "zscore", "statistical"],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStrategies();
  }, []);

  async function handleScaffold(e: React.FormEvent) {
    e.preventDefault();
    if (!scaffoldForm.name.trim()) {
      toast.error("Strategy name is required");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.scaffoldStrategy(scaffoldForm);
      toast.success(result.message);
      setShowForm(false);
      setScaffoldForm({ name: "", description: "" });
      await loadStrategies();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to scaffold strategy");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Strategies</h1>
          <p className="text-muted-foreground">Registered strategies and templates</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadStrategies} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="mr-2 h-4 w-4" />
            New Strategy
          </Button>
        </div>
      </div>

      {showForm && (
        <Card className="bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-lg">New Strategy Scaffold</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleScaffold} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    placeholder="my-strategy"
                    value={scaffoldForm.name}
                    onChange={(e) =>
                      setScaffoldForm((f) => ({ ...f, name: e.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description (optional)</Label>
                  <Input
                    placeholder="Describe your strategy..."
                    value={scaffoldForm.description}
                    onChange={(e) =>
                      setScaffoldForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Scaffolding…" : "Create Strategy"}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {loading ? (
          <>
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </>
        ) : strategies.length === 0 ? (
          <Card className="bg-card/50 backdrop-blur">
            <CardContent className="p-8 text-center">
              <Code2 className="mx-auto h-10 w-10 text-muted-foreground/50 mb-3" />
              <p className="text-muted-foreground">No strategies registered yet.</p>
            </CardContent>
          </Card>
        ) : (
          strategies.map((s) => (
            <Card key={s.name} className="bg-card/50 backdrop-blur transition-colors hover:bg-muted/50">
              <CardContent className="py-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <FileCode2 className="h-5 w-5 text-primary" />
                      <span className="font-mono text-lg font-semibold">{s.name}</span>
                      {s.version && (
                        <Badge variant="outline">{s.version}</Badge>
                      )}
                    </div>
                    {s.description && (
                      <p className="text-sm text-muted-foreground">{s.description}</p>
                    )}
                    {s.tags && s.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {s.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            <Tag className="mr-1 h-3 w-3" />
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="text-right text-sm text-muted-foreground">
                    {s.module_path && <div className="font-mono">{s.module_path}</div>}
                    {s.registered_at && <div>{new Date(s.registered_at).toLocaleDateString()}</div>}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
