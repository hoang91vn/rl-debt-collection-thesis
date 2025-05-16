from datetime import datetime
from typing import Any, Dict, Final, List
from clients_code import Client
import numpy as np
import pandas as pd
import os
from abt import run
from constants import RUN_DATA_PATH, PLAYGROUND_DIR, CURRENT_DIR
from summary import (
    calculate_period_cost,
    calculate_period_revenue,
    calculate_revenue,
    calculate_cost,
)


TEST_DATA_PATH: Final[str] = "/home/akmere/Projects/rl-debt-collection/tests/test_data"
SIMULATION_DATA_PATH = os.path.join(TEST_DATA_PATH, "simulate/data")

if not os.path.exists(RUN_DATA_PATH):
    os.makedirs(RUN_DATA_PATH)


def choose_actions(path: str, aids: List[str]) -> Dict[str, str]:
    actions: Dict[str, str] = {}
    for aid in aids:
        actions[aid] = "1"
    return actions


def simulate_reactions(
    path: str, actions: Dict[str, str], period: int
) -> Dict[str, bool]:
    reactions: Dict[str, bool] = {}
    for aid, action in actions.items():
        reactions[aid] = True
    return reactions


def get_action_cost(action: str) -> int:
    return 50


if __name__ == "__main__":
    generator = np.random.default_rng(42)
    # run(
    #     RUN_DATA_PATH,
    #     20260501,
    #     2,
    #     2,
    #     generator,
    #     choose_actions,
    #     simulate_reactions,
    #     start_date=20240501,
    #     overwrite=True,
    # )
    print(calculate_period_revenue(SIMULATION_DATA_PATH, 200010))
    print(calculate_period_cost(SIMULATION_DATA_PATH, 200010, get_action_cost))
    print(calculate_revenue(SIMULATION_DATA_PATH, 200003, 200107))
    print(calculate_revenue(SIMULATION_DATA_PATH, None, None))
    print(calculate_cost(SIMULATION_DATA_PATH, 200003, 200107, get_action_cost))
    print(calculate_cost(SIMULATION_DATA_PATH, None, None, get_action_cost))
