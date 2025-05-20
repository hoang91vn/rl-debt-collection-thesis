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
from util import get_all_accounts_histories


TEST_DATA_PATH: Final[str] = "/home/akmere/Projects/rl-debt-collection/tests/test_data"
SIMULATION_DATA_PATH = os.path.join(TEST_DATA_PATH, "simulate/data")

if not os.path.exists(RUN_DATA_PATH):
    os.makedirs(RUN_DATA_PATH)


def choose_actions(data_path: str, aids: List[str]) -> Dict[str, str]:
    actions: Dict[str, str] = {}
    for aid in aids:
        actions[aid] = "2"
    return actions


def simulate_reactions(
    data_path: str, actions: Dict[str, str], period: int
) -> Dict[str, bool]:
    reactions: Dict[str, bool] = {}
    for aid, action in actions.items():
        if action == "1":
            reactions[aid] = True
        else:
            reactions[aid] = False
    return reactions


def get_action_cost(action: str) -> int:
    return 50


if __name__ == "__main__":
    # generator = np.random.default_rng(42)
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
    # revenue: int = calculate_revenue(RUN_DATA_PATH, None, None)
    # cost: int = calculate_cost(RUN_DATA_PATH, None, None, get_action_cost)
    # print(f"revenue: {revenue}, cost: {cost}, profit: {revenue - cost}")
    history = get_all_accounts_histories(RUN_DATA_PATH)
    # print(history)
