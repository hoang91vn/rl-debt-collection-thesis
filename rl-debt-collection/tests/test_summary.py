from typing import Final
from rl_debt_collection.summary import (
    calculate_period_cost,
    calculate_period_revenue,
    calculate_cost,
    calculate_revenue,
)
import os

TEST_DATA_PATH: Final[str] = os.path.join(os.path.dirname(__file__), "test_data")


def test_calculate_period_cost(benchmark):
    def get_action_cost(action: str) -> int:
        return 50

    cost: int = benchmark(
        calculate_period_cost,
        os.path.join(TEST_DATA_PATH, "simulate/data"),
        200109,
        get_action_cost,
    )

    assert cost == 25600


def test_calculate_period_revenue(benchmark):
    revenue: int = benchmark(
        calculate_period_revenue, os.path.join(TEST_DATA_PATH, "simulate/data"), 200109
    )
    assert revenue == 106154


def test_calculate_revenue_range(benchmark):
    revenue_range: int = benchmark(
        calculate_revenue, os.path.join(TEST_DATA_PATH, "simulate/data"), 200003, 200107
    )
    assert revenue_range == 1111837


def test_calculate_revenue_total(benchmark):
    revenue_total: int = benchmark(
        calculate_revenue, os.path.join(TEST_DATA_PATH, "simulate/data"), None, None
    )
    assert revenue_total == 1798440


def test_calculate_cost_range(benchmark):
    def get_action_cost(action: str) -> int:
        return 50

    cost_range: int = benchmark(
        calculate_cost,
        os.path.join(TEST_DATA_PATH, "simulate/data"),
        200003,
        200107,
        get_action_cost,
    )
    assert cost_range == 246750


def test_calculate_cost_total(benchmark):
    def get_action_cost(action: str) -> int:
        return 50

    cost_total: int = benchmark(
        calculate_cost,
        os.path.join(TEST_DATA_PATH, "simulate/data"),
        None,
        None,
        get_action_cost,
    )
    assert cost_total == 408900
