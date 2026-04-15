import rl_debt_collection
from rl_debt_collection import summary
from typing import Dict, Final, List
import os
import numpy as np

RUN_DATA_PATH: Final[str] = "runs/thesis_baseline"
if not os.path.exists(RUN_DATA_PATH):
    os.makedirs(RUN_DATA_PATH)

SEED: Final[int] = 42
P_POSITIVE: Final[float] = 0.05

_reaction_rng: Final[np.random.Generator] = np.random.default_rng(SEED + 1)


def choose_actions(data_path: str, aids: List[str]) -> Dict[str, str]:
    actions: Dict[str, str] = {}
    for aid in aids:
        actions[aid] = "1"
    return actions


def simulate_reactions(
    data_path: str, actions: Dict[str, str], period: int
) -> Dict[str, bool]:
    reactions: Dict[str, bool] = {}
    for aid, action in actions.items():
        reactions[aid] = bool(_reaction_rng.random() < P_POSITIVE)
    return reactions


def get_action_cost(action: str) -> int:
    return 5


def main():
    rl_debt_collection.run(
        data_path=RUN_DATA_PATH,
        end_date=20290501,
        new_clients_count=50,
        choose_actions_func=choose_actions,
        simulate_reactions_func=simulate_reactions,
        start_date=20240501,
        overwrite=True,
        generator=np.random.default_rng(SEED),
    )
    revenue = summary.calculate_revenue(RUN_DATA_PATH, None, None)
    cost = summary.calculate_cost(RUN_DATA_PATH, None, None, get_action_cost)
    print(f"seed={SEED} p_positive={P_POSITIVE} revenue={revenue} cost={cost} profit={revenue-cost}")


if __name__ == "__main__":
    main()
