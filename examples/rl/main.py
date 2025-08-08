from datetime import datetime
from typing import Any, Dict, Final, List
from rl_debt_collection.clients_code import Client
import numpy as np
import pandas as pd
import os
from rl_debt_collection import run
from rl_debt_collection.summary import (
    calculate_period_cost,
    calculate_period_revenue,
    calculate_revenue,
    calculate_cost,
)
from transformation import (
    DISCRETE_VARIABLES,
    transform,
    transform_observation,
    get_state_space_size,
    get_statistics,
)
from environment import ACTIONS
from models import load_or_create_model
from rl_debt_collection.util import (
    get_all_accounts_histories,
    get_relative_period,
    load_transactions_table,
)
from rl_decision import get_best_action, model_on_history, transform_histories
import torch

RUN_DATA_PATH: Final[str] = "runs/a"
MODEL_PATH: str = "models/model"

if not os.path.exists(RUN_DATA_PATH):
    os.makedirs(RUN_DATA_PATH)

GAMMA: Final[float] = 0.05


def choose_actions(data_path: str, aids: List[str]) -> Dict[str, str]:
    actions: Dict[str, str] = {}
    histories = get_all_accounts_histories(RUN_DATA_PATH)
    transactions_df = load_transactions_table(data_path, False)
    last_period: int = get_relative_period(
        transactions_df.index.get_level_values("period").astype(int).max(), -1
    )
    terminated_histories_count = len(
        [
            (key, history)
            for (key, history) in histories.items()
            if history["terminated"]
        ]
    )
    model = load_or_create_model(MODEL_PATH, get_state_space_size(), len(ACTIONS), None)
    statistics = get_statistics(
        pd.read_csv(os.path.join(data_path, f"abt_base_{last_period}.csv"))
    )
    transformed_histories = transform_histories(histories, statistics)
    if terminated_histories_count > 0:
        model = model_on_history(
            accounts_histories=transformed_histories,
            model=model,
            input_size=get_state_space_size(),
            output_size=len(ACTIONS),
            discount_factor=GAMMA,
            n_step=2,
            iterations=50,
            batch_size=1000,
            learning_rate=0.01,
            whole_buffer=False,
            reward_scheme="1",
            target_network_interval=1,
            statistics=statistics,
        )
        torch.save(model.state_dict(), MODEL_PATH)
    for aid in aids:
        action: str = np.random.choice(ACTIONS)
        if aid in transformed_histories:
            last_account_period_info = transformed_histories[aid]["history"][-2]
            assert last_account_period_info["abt_data"] is not None
            action = get_best_action(
                last_account_period_info["abt_data"],
                model,
                last_account_period_info["transactions_data"]["coll_status"],
            )
        actions[aid] = action
    return actions


def simulate_reactions(
    data_path: str, actions: Dict[str, str], period: int
) -> Dict[str, bool]:
    reactions: Dict[str, bool] = {}
    for aid, action in actions.items():
        if action == "2":
            reactions[aid] = True
        else:
            reactions[aid] = False
    return reactions


def get_action_cost(action: str) -> int:
    return 50


if __name__ == "__main__":
    generator = np.random.default_rng(42)
    run(
        RUN_DATA_PATH,
        20260501,
        2,
        2,
        generator,
        choose_actions,
        simulate_reactions,
        start_date=20240501,
        overwrite=True,
    )
    revenue: int = calculate_revenue(RUN_DATA_PATH, None, None)
    cost: int = calculate_cost(RUN_DATA_PATH, None, None, get_action_cost)
    print(f"revenue: {revenue}, cost: {cost}, profit: {revenue - cost}")
    history = get_all_accounts_histories(RUN_DATA_PATH)
    terminated_histories_count = len(
        [(key, history) for (key, history) in history.items() if history["terminated"]]
    )
    active_histories_count = len(history.items()) - terminated_histories_count
    print(f"active: {active_histories_count}, terminated: {terminated_histories_count}")
