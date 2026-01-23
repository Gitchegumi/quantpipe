# pylint: disable=unused-import

from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace

from src.cli.main import main as run_main
from src.cli.run_backtest import logger as run_logger
import argparse


def infer_pair_from_path(p: Path) -> str | None:
    for part in p.parts[::-1]:
        part_lower = part.lower()
        if len(part_lower) == 6 and part_lower.isalpha():
            return part_lower.upper()
    return None


def test_infer_pair_from_path_usdjpy():
    path = Path("price_data/processed/usdjpy/test/usdjpy_test.csv")
    assert infer_pair_from_path(path) == "USDJPY"


def test_infer_pair_from_path_eurusd():
    path = Path("price_data/processed/eurusd/train/eurusd_train.csv")
    assert infer_pair_from_path(path) == "EURUSD"


def test_infer_pair_from_path_none():
    path = Path("price_data/processed/other/data.csv")
    assert infer_pair_from_path(path) is None
