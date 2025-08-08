from typing import Dict, Final, List, Tuple

import numpy as np
import pandas as pd

ACTIONS: Final[List[str]] = [
    "0",
    "1",
    "2",
    "3",
    "11",
    "12",
    "22",
    "32",
    "33",
    "122",
    "222",
    "322",
    "332",
    "333",
]

ACTION_COST: Final[Dict[str, float]] = {
    "0": 0.0,
    "1": 5.0,
    "2": 15.0,
    "3": 30.0,
}

ACTION_HARSHNESS: Final[Dict[str, float]] = {
    "0": 0.0,
    "1": 0.1,
    "2": 0.3,
    "3": 0.5,
}


def get_available_actions(coll_status: int) -> List[str]:
    match coll_status:
        case 1:
            return ["0"]
        case 2:
            return ["0", "1", "11", "12", "122", "333"]
        case 3:
            return ["0", "1", "2", "22", "222", "333"]
        case 4:
            return ["0", "2", "3", "22", "222", "333"]
        case 5:
            return ["0", "2", "3", "32", "322", "333"]
        case 6:
            return ["0", "2", "3", "33", "332", "333"]
        case 7:
            return ["0"]
        case _:
            return ["0"]


def get_action_cost(actions_str: str) -> float:
    cost: float = 0.0
    for action in actions_str:
        cost += ACTION_COST[action]
    return cost


def get_actions_harshness() -> Dict[str, float]:
    actions_harshness: Dict[str, float] = {}
    for action in ACTIONS:
        harshness: float = 0.0
        for char in action:
            harshness += ACTION_HARSHNESS[char]
        actions_harshness[action] = harshness
    return actions_harshness


def get_action_harshness(actions_str: str) -> float:
    harshness: float = 0.0
    for char in actions_str:
        harshness += ACTION_HARSHNESS[char]
    return harshness


def get_action_injustice(action: str, coll_status: str) -> float:
    INJUSTICE_MAP: Dict[str, Dict[str, float]] = {
        "1": {"1": 0.1, "2": 0.3, "3": 0.5},
        "2": {"2": 0.1, "3": 0.3},
        "3": {"2": 0.1, "3": 0.2},
        "4": {"3": 0.2},
        "5": {"3": 0.1},
        "6": {},
        "7": {"1": 0.05, "2": 0.25, "3": 0.45},
    }
    injustice = sum(
        INJUSTICE_MAP[coll_status].get(subaction, 0) for subaction in action
    )

    for i in range(len(action) - 1):
        if int(action[i]) < int(action[i + 1]):
            injustice += 0.1

    return injustice


def calculate_positive_reaction(
    harshness: float,
    injustice: float,
    stress: float,
    vindictiveness: float,
) -> int:
    # stress is the best at 3
    stress_deviation = abs(stress - 3.0)
    prob_base: float = 0.7
    prob: float = (
        prob_base
        - 0.1 * stress_deviation
        - 0.1 * vindictiveness
        + 0.5 * harshness
        - 0.2 * injustice
    )
    # clamp probability to [0,1]
    prob = max(0.0, min(1.0, prob))
    return np.random.choice([0, 1], p=[1 - prob, prob])


def get_personally_adjusted_harshness_injustice_stress_sentiment(
    harshness: float,
    injustice: float,
    stress: float,
    vindictiveness: float,
    abt_row: pd.Series,
) -> Tuple[float, float, float, float]:
    harshness_multiplier: float = 1.0
    injustice_multiplier: float = 1.0
    stress_multiplier: float = 1.0
    vindictiveness_multiplier: float = 1.0
    age: float = abt_row["act_age"]
    # older people stress less but have better sentiment
    stress_multiplier -= (age - 55.0) / 55.0 * 0.3
    vindictiveness_multiplier -= (age - 55.0) / 55.0 * 0.3
    city: float = abt_row["app_nom_city"]  # discrete value [1,2,3,4]
    # big cities stress less
    stress_multiplier -= (city - 2.5) / 1.5 * 0.3
    marital_status = abt_row["app_nom_marital_status"]  # discrete value [1,2,3,4]
    # married stress more and have better sentiment, divorces people are more vindictive
    if marital_status == 4.0:
        stress_multiplier += 0.3
        vindictiveness_multiplier -= 0.3
    elif marital_status == 2.0:
        vindictiveness_multiplier += 0.5
    is_car_owner: bool = abt_row["app_nom_cars"] == 2.0  # boolean
    # car owners stress less
    if is_car_owner:
        stress_multiplier -= 0.2
    is_male: bool = abt_row["app_nom_gender"] == 1.0  # boolean
    number_of_children = abt_row["app_number_of_children"]
    stress_multiplier += number_of_children * 0.05
    vindictiveness_multiplier -= number_of_children * 0.05
    home_status = abt_row["app_nom_home_status"]  # discrete value [1,2,3]
    if home_status == 1.0:
        stress_multiplier -= 0.2
    if home_status == 3.0:
        vindictiveness_multiplier -= 0.2
    branch = abt_row["app_nom_branch"]  # discrete value [1,2,3,4]
    if branch == 1.0:
        injustice_multiplier += 0.2
    if branch == 2.0:
        stress_multiplier -= 0.2
    job_code = abt_row["app_nom_job_code"]  # discrete value [1,2,3,4]
    if job_code == 4.0:
        harshness_multiplier += 0.4
        vindictiveness_multiplier -= 0.1

    # print multipliers
    # print(
    #     harshness_multiplier,
    #     injustice_multiplier,
    #     stress_multiplier,
    #     vindictiveness_multiplier,
    # )
    return (
        harshness * harshness_multiplier,
        injustice * injustice_multiplier,
        stress * stress_multiplier,
        vindictiveness * vindictiveness_multiplier,
    )


ACTIONS_HARSHNESS: Final[Dict[str, float]] = get_actions_harshness()
