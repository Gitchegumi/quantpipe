# Issue: QuantPipe Web Dashboard — Implementation Notes

## Branch
`issue/quantpipe-web-dashboard`

## Scope
Full Next.js 15 + FastAPI web dashboard for QuantPipe FOREX backtesting engine.

## Deliverables Created

### 1. FastAPI Backend (`quantpipe_api/`)
- **`main.py`** — FastAPI app with CORS, lifespan context, all REST endpoints + SSE streaming
- **`models.py`** — Pydantic schemas: BacktestRequest, BacktestStatus, BacktestResult, ProgressEvent, TradeRecord, EquityPoint, etc.
- **`engine_wrapper.py`** — Background task runner with ThreadPoolExecutor, monkey-patches ProgressDispatcher to push to asyncio Queue for SSE
- **`requirements.txt`** — API-only deps (redundant with Poetry group but provided)

#### Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/strategies` | List STRATEGY_MAP entries |
| GET | `/api/pairs` | Scan price_data/processed/ |
| POST | `/api/backtest` | Start backtest → `{runId}` |
| GET | `/api/backtest/{runId}` | Status |
| GET | `/api/backtest/{runId}/stream` | SSE progress stream |
| GET | `/api/backtest/{runId}/results` | Final results JSON |
| GET | `/api/backtest/{runId}/log` | Log output |
| DELETE | `/api/backtest/{runId}` | Cancel run |
| GET | `/api/backtests` | List all runs |

#### Progress Streaming
- Monkey-patches `ProgressDispatcher` at runtime via context manager
- Captures scan/simulate phases, pushes to per-run `asyncio.Queue`
- SSE endpoint consumes queue with heartbeat/timeout handling
- Runs persist to `results/backtest_runs.json` (append-only, reload on startup)

### 2. Docker Compose (`docker/`)
- **`docker-compose.yml`** — Two-service setup with volume mounts, env vars, healthcheck
- **`api.Dockerfile`** — Python 3.12 slim, Poetry install, PYTHONPATH=/app/src, CMD uvicorn

### 3. Next.js UI (`quantpipe-ui/`)
- **`package.json`** — Next.js 15, React 19, shadcn deps, Recharts, TanStack Table, react-hook-form, zod, next-themes, lucide-react
- **`tsconfig.json`** / **`tailwind.config.ts`** / **`postcss.config.mjs`** / **`next.config.ts`** — Standard modern Next.js config
- **`app/globals.css`** — Dark mode default, Tailwind + CSS vars
- **`app/layout.tsx`** — ThemeProvider (dark default), Sidebar layout

#### Routes (App Router)
| Route | Purpose |
|-------|---------|
| `/` | Dashboard — stats cards + recent runs table |
| `/backtest` | New backtest form — strategy dropdown, pair multi-select, direction/dataset/timeframe/sim-type, risk sliders, advanced collapsible |
| `/monitor/[runId]` | Live progress — progress bar, phase label, log terminal, auto-redirect to results |
| `/results/[runId]` | Results viewer — summary cards (return, win rate, profit factor, max DD, Sharpe), equity curve (Recharts AreaChart), trade table with direction badges, export JSON/CSV |
| `/strategies` | Strategy browser with tags |
| `/settings` | Theme toggle + API URL display |

#### shadcn/ui Components (custom build)
- Card, Button, Label, Select, Progress, Badge, Input, RadioGroup, Slider
- All use `cn()` utility from `lib/utils.ts`

#### Hooks
- **`useBacktest.ts`** — `apiFetch` helper + `useBacktest()` hook (start, status, results, log, cancel, listRuns, listStrategies, listPairs)
- **`useSse(url)`** — SSE connection with auto-reconnect, heartbeat handling, done/failed/cancelled detection

#### Theme
- Dark mode default via `next-themes`, slate tokens
- Color scheme: emerald (gains), rose (losses), amber (running/waiting), slate (neutral)

### 4. Updated `pyproject.toml`
- Added `[tool.poetry.group.api.dependencies]` with `fastapi` and `uvicorn[standard]`

## Design Decisions

1. **Module name `quantpipe_api`** (underscore) because Python cannot import packages with hyphens. The task spec used `quantpipe-api/` which I preserved as the directory name initially, but moved to `quantpipe_api/` for Python importability.

2. **ThreadPoolExecutor instead of BackgroundTasks** — The backtest is CPU-bound (numpy/polars). FastAPI's `BackgroundTasks` runs in the event loop and would block all requests. ThreadPoolExecutor keeps the API responsive. No `asyncio.create_task` used.

3. **ProgressDispatcher monkey-patch** — Cleanest way to hook into existing progress infrastructure without touching QuantPipe source files. The patch is scoped to the backtest run via context manager and fully restored afterward.

4. **No `fastapi` dependency in `requirements.txt`** — The API deps are in `pyproject.toml`'s `[tool.poetry.group.api.dependencies]`. The Dockerfile uses Poetry install, so `requirements.txt` is a convenience reference only.

5. **Equity curve estimation** — The `BacktestResult` dataclass from QuantPipe doesn't include an equity curve field, so `_serialize_single` builds one by iterating executions and applying a fixed 1% risk-per-trade model. This is a simplification but provides the UI chart data.

6. **Next.js `output: standalone`** — Docker image uses multi-stage build with Node 22 Alpine for minimal final image.

## Known Limitations / Future Work

- The equity curve is estimated (not computed by the engine). A future enhancement could have `run_portfolio_backtest` return per-trade equity.
- Log streaming is stubbed (returns status-based lines). Real log capture would pipe orchestrator logs to a file per run.
- Pair multi-select uses simple toggle buttons. A proper combobox/multi-select with search would be better for large pair lists.
- The UI Dockerfile uses `next.config.ts` (standalone output) — this is correct for Next.js 15 but requires `sharp` to be installed for image optimization in production.

## Testing Notes

- `python3 -c "import sys; sys.path.insert(0, 'src'); import quantpipe_api.main; print('OK')"` passes
- `python3 -c "import sys; sys.path.insert(0, 'src'); import quantpipe_api.engine_wrapper; print('OK')"` passes
- Docker build not tested locally (requires price_data + poetry.lock sync)
