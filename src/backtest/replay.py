from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import pandas as pd
from src.infrastructure.duckdb.vault import DuckDBVault

logger = logging.getLogger(__name__)


class ReplaySession:
    """
    Manages a stateful market replay session, providing candles one-by-one or in chunks.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        vault_path: str = "data/vault.duckdb",
        buffer_size: int = 1000,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time = start_time
        self.end_time = end_time
        self.vault_path = vault_path
        self.buffer_size = buffer_size

        self.current_time = start_time
        self.vault = DuckDBVault(db_path=vault_path)

        # Pre-load initial buffer
        self._buffer = pd.DataFrame()
        self._buffer_idx = 0
        self._load_next_buffer()

    def _load_next_buffer(self):
        """Loads the next chunk of data from the vault into the memory buffer."""
        # Calculate end of fetch window
        # For simplicity, we just fetch a fixed number of rows or a fixed time range
        # Here we fetch based on time to ensure we cover the range
        fetch_end = self.current_time + timedelta(days=1)  # Fetch 1 day at a time
        if fetch_end > self.end_time:
            fetch_end = self.end_time

        self._buffer = self.vault.fetch_range(
            self.symbol,
            self.timeframe,
            self.current_time.strftime("%Y-%m-%d %H:%M:%S"),
            fetch_end.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._buffer_idx = 0

        if not self._buffer.empty:
            logger.debug("Replay buffer refilled: %s bars.", len(self._buffer))

    def next_candle(self) -> Optional[Dict[str, Any]]:
        """Returns the next candle in the sequence."""
        if self._buffer_idx >= len(self._buffer):
            if self.current_time >= self.end_time:
                return None
            self._load_next_buffer()
            if self._buffer.empty:
                return None

        row = self._buffer.iloc[self._buffer_idx]
        self._buffer_idx += 1
        self.current_time = row["timestamp"]

        return row.to_dict()

    def reset(self):
        """Resets the session to the start time."""
        self.current_time = self.start_time
        self._load_next_buffer()

    def close(self):
        self.vault.close()


def main():
    """Main entry point for the replay CLI."""
    print("Replay Mode")
    print("=" * 60)

    # Get parameters from user
    symbol = input("Symbol (e.g., EURUSD): ").strip().upper()
    timeframe = input("Timeframe (e.g., M15): ").strip().upper()
    start_str = input("Start time (YYYY-MM-DD HH:MM): ").strip()
    end_str = input("End time (YYYY-MM-DD HH:MM): ").strip()

    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD HH:MM")
        return

    # Create replay session
    session = ReplaySession(symbol, timeframe, start_time, end_time)

    # Replay loop
    print("\nStarting replay... Press Ctrl+C to stop.")
    print("-" * 60)

    try:
        while True:
            candle = session.next_candle()
            if candle is None:
                break

            # Print candle info
            print(
                f"{candle['timestamp']} | "
                f"O={candle['open']:.5f} | "
                f"H={candle['high']:.5f} | "
                f"L={candle['low']:.5f} | "
                f"C={candle['close']:.5f} | "
                f"V={candle['volume']}"
            )
    except KeyboardInterrupt:
        print("\nReplay stopped by user.")
    finally:
        session.close()
        print("Session closed.")


if __name__ == "__main__":
    main()
