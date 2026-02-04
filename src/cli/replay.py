import argparse
import logging
import sys
from datetime import datetime, timedelta
from src.backtest.replay import ReplaySession
from src.visualization.replay_dashboard import ReplayDashboard

logger = logging.getLogger(__name__)

def run_replay_command(args):
    """Executes the market replay CLI command."""
    # Convert dates
    start_time = datetime.strptime(args.start, "%Y-%m-%d")
    end_time = datetime.strptime(args.end, "%Y-%m-%d")
    
    session = ReplaySession(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_time=start_time,
        end_time=end_time,
        vault_path=args.vault_path
    )
    
    dashboard = ReplayDashboard(session)
    dashboard.show()

def main():
    parser = argparse.ArgumentParser(description="Market Replay CLI")
    parser.add_argument("--symbol", type=str, required=True, help="Symbol to replay")
    parser.add_argument("--timeframe", type=str, default="1m", help="Timeframe (default: 1m)")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--vault-path", type=str, default="data/vault.duckdb", help="Path to DuckDB vault")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    run_replay_command(args)

if __name__ == "__main__":
    main()
