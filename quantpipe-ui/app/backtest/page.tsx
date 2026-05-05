"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { useBacktest } from "@/hooks/useBacktest";
import { PlayCircle, ChevronDown, ChevronUp } from "lucide-react";

export default function BacktestPage() {
  const router = useRouter();
  const { listStrategies, listPairs, start } = useBacktest();
  const [strategies, setStrategies] = useState<{ name: string; description: string }[]>([]);
  const [pairs, setPairs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // Form state
  const [strategy, setStrategy] = useState("trend-pullback");
  const [selectedPairs, setSelectedPairs] = useState<string[]>([]);
  const [direction, setDirection] = useState<"LONG" | "SHORT" | "BOTH">("LONG");
  const [dataset, setDataset] = useState<"test" | "validate">("test");
  const [timeframe, setTimeframe] = useState("1m");
  const [simType, setSimType] = useState<"personal_capital" | "cti">("personal_capital");
  const [startingEquity, setStartingEquity] = useState(2500);
  const [maxRisk, setMaxRisk] = useState([1.0]);
  const [slMult, setSlMult] = useState([1.0]);
  const [tpMult, setTpMult] = useState([2.0]);
  const [dryRun, setDryRun] = useState(false);
  const [profiling, setProfiling] = useState(false);

  useEffect(() => {
    listStrategies().then((s) => {
      setStrategies(s);
      if (s.length > 0) setStrategy(s[0].name);
    });
    listPairs().then((p) => {
      setPairs(p);
      if (p.length > 0) setSelectedPairs([p[0]]);
    });
  }, [listStrategies, listPairs]);

  const togglePair = (p: string) => {
    setSelectedPairs((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedPairs.length === 0) return;
    setLoading(true);
    try {
      const runId = await start({
        strategy,
        pairs: selectedPairs,
        direction,
        dataset,
        timeframe: timeframe as any,
        simulation_type: simType,
        starting_equity: startingEquity,
        max_risk_pct: maxRisk[0],
        sl_multiplier: slMult[0],
        tp_multiplier: tpMult[0],
        dry_run: dryRun,
        profiling,
      });
      router.push(`/monitor/${runId}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New Backtest</h1>
        <p className="text-muted-foreground">Configure and launch a backtest run.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Strategy */}
            <div className="space-y-2">
              <Label>Strategy</Label>
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((s) => (
                    <SelectItem key={s.name} value={s.name}>
                      {s.name}
                      {s.description && (
                        <span className="text-muted-foreground ml-2 text-xs">— {s.description}</span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Pairs */}
            <div className="space-y-2">
              <Label>Pairs</Label>
              <div className="flex flex-wrap gap-2">
                {pairs.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => togglePair(p)}
                    className={`px-3 py-1 rounded-md text-sm border transition-colors ${
                      selectedPairs.includes(p)
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-card text-muted-foreground border-border hover:bg-accent"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Direction */}
            <div className="space-y-2">
              <Label>Direction</Label>
              <RadioGroup
                value={direction}
                onValueChange={(v) => setDirection(v as any)}
                className="flex gap-4"
              >
                {(["LONG", "SHORT", "BOTH"] as const).map((d) => (
                  <div key={d} className="flex items-center space-x-2">
                    <RadioGroupItem value={d} id={`dir-${d}`} />
                    <Label htmlFor={`dir-${d}`} className="cursor-pointer">{d}</Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            {/* Dataset */}
            <div className="space-y-2">
              <Label>Dataset</Label>
              <RadioGroup
                value={dataset}
                onValueChange={(v) => setDataset(v as any)}
                className="flex gap-4"
              >
                {(["test", "validate"] as const).map((d) => (
                  <div key={d} className="flex items-center space-x-2">
                    <RadioGroupItem value={d} id={`ds-${d}`} />
                    <Label htmlFor={`ds-${d}`} className="cursor-pointer">{d === "test" ? "Test" : "Validation"}</Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            {/* Timeframe */}
            <div className="space-y-2">
              <Label>Timeframe</Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["1m", "5m", "15m", "1h", "4h", "1d"].map((tf) => (
                    <SelectItem key={tf} value={tf}>{tf}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Simulation Type */}
            <div className="space-y-2">
              <Label>Simulation Type</Label>
              <Select value={simType} onValueChange={(v) => setSimType(v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="personal_capital">Personal Capital</SelectItem>
                  <SelectItem value="cti">CTI (Prop Firm)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Starting Equity */}
            <div className="space-y-2">
              <Label>Starting Equity ($)</Label>
              <Input
                type="number"
                value={startingEquity}
                onChange={(e) => setStartingEquity(Number(e.target.value))}
                min={100}
              />
            </div>

            {/* Risk Sliders */}
            <div className="space-y-4">
              <div>
                <Label>Max Risk per Trade: {maxRisk[0]}%</Label>
                <Slider value={maxRisk} onValueChange={setMaxRisk} min={0.1} max={10} step={0.1} />
              </div>
              <div>
                <Label>SL Multiplier: {slMult[0]}x</Label>
                <Slider value={slMult} onValueChange={setSlMult} min={0.1} max={5} step={0.1} />
              </div>
              <div>
                <Label>TP Multiplier: {tpMult[0]}x</Label>
                <Slider value={tpMult} onValueChange={setTpMult} min={0.1} max={10} step={0.1} />
              </div>
            </div>

            {/* Advanced */}
            <div className="border-t pt-4">
              <button
                type="button"
                onClick={() => setAdvancedOpen(!advancedOpen)}
                className="flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {advancedOpen ? <ChevronUp className="h-4 w-4 mr-1" /> : <ChevronDown className="h-4 w-4 mr-1" />}
                Advanced Options
              </button>
              {advancedOpen && (
                <div className="mt-4 space-y-4">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="dry-run"
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <Label htmlFor="dry-run">Dry Run (signals only, no execution)</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="profiling"
                      checked={profiling}
                      onChange={(e) => setProfiling(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <Label htmlFor="profiling">Enable Profiling</Label>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4">
              <Button type="submit" disabled={loading || selectedPairs.length === 0} className="w-full">
                <PlayCircle className="mr-2 h-4 w-4" />
                {loading ? "Starting..." : "Start Backtest"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
