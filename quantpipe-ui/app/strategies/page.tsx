"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useBacktest } from "@/hooks/useBacktest";
import { FlaskConical } from "lucide-react";

interface StrategyInfo {
  name: string;
  description: string;
  tags: string[];
}

export default function StrategiesPage() {
  const { listStrategies } = useBacktest();
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listStrategies()
      .then((s) => setStrategies(s))
      .finally(() => setLoading(false));
  }, [listStrategies]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Strategies</h1>
        <p className="text-muted-foreground">Available backtesting strategies.</p>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {strategies.map((s) => (
            <Card key={s.name}>
              <CardHeader className="flex flex-row items-center gap-3">
                <FlaskConical className="h-5 w-5 text-primary" />
                <div>
                  <CardTitle className="text-base">{s.name}</CardTitle>
                  <CardDescription>{s.description || "No description"}</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1">
                  {s.tags?.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  )) || <span className="text-xs text-muted-foreground">No tags</span>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
