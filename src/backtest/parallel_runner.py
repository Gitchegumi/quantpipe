"""
This module provides a parallel execution runner for backtesting simulations.
"""

from joblib import Parallel, delayed

def run_in_parallel(tasks):
    """
    Runs a list of tasks in parallel using joblib.

    Args:
        tasks: A list of tuples, where each tuple contains the function
               to execute and its arguments.

    Returns:
        A list of results from the executed tasks.
    """
    results = Parallel(n_jobs=-1)(delayed(func)(*args) for func, *args in tasks)
    return results
