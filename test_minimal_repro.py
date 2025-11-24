"""Minimal reproduction of the dataclass error."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
from polars import DataFrame as PolarsDataFrame

# Try different type hint styles
print("Test 1: Simple dataclass")


@dataclass
class Test1:
    value: int


t1 = Test1(value=1)
print("Test 1: SUCCESS")

print("\nTest 2: Union with |")


@dataclass
class Test2:
    data: pd.DataFrame | PolarsDataFrame


print("Test 2 class defined")
t2 = Test2(data=pd.DataFrame())
print("Test 2: SUCCESS")
