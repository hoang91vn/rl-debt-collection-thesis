from typing import List, Final
import pandas as pd
from special_types import (
    AccountTwoPeriodInfo,
    CollectionActionRow,
)
import numpy as np

ACTIONS: Final[List[str]] = [
    "0",
    "1",
    "2",
    "3",
    "12",
    "13",
    "21",
    "23",
    "31",
    "32",
    "11",
    "22",
    "33",
    "123",
    "132",
    "213",
    "231",
    "312",
    "321",
    "112",
    "113",
    "121",
    "131",
    "122",
    "133",
    "211",
    "223",
    "221",
    "233",
    "311",
    "331",
    "332",
    "212",
    "232",
    "313",
    "323",
    "111",
    "222",
    "322",
    "333",
]


def decide_for_all(
    info: List[AccountTwoPeriodInfo],
) -> List[CollectionActionRow]:
    decisions: List[CollectionActionRow] = []
    for two_period_info in info:
        last_state = two_period_info["previous"]["abt_data"]
        last_action = two_period_info["previous"]["action"]
        current_state = two_period_info["current"]["abt_data"]
        assert two_period_info["current"]["transactions_data"] is not None
        status = two_period_info["current"]["transactions_data"]["status"]
        terminated: bool = status != "A"
        if last_state is not None and last_action is not None:
            # place to update a model with a new transition
            pass
        if not terminated and current_state is not None:
            action_str: str = "0"
            if two_period_info["current"]["transactions_data"]["coll_status"] not in [
                1,
                7,
            ]:
                action_str: str = decide(current_state)
            action_nr: int = 1
            for action in action_str[::-1]:
                decisions.append(
                    {
                        "cid": two_period_info["cid"],
                        "aid": two_period_info["current"]["aid"],
                        "period": two_period_info["current"]["period"],
                        "action_nr": action_nr,
                        "action": int(action),
                        "coll_status": two_period_info["current"]["transactions_data"][
                            "coll_status"
                        ],
                    }
                )
                action_nr += 1
    return decisions


def decide(new_state: pd.Series) -> str:
    epsilon = 1.0
    if np.random.rand() < epsilon:
        actions_str = np.random.choice(ACTIONS)
    else:
        # mechanism for choosing the best action
        actions_str = "123"
    return actions_str
