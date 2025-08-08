import rl_debt_collection
from rl_debt_collection import summary
from typing import Dict, Final, List
import os

RUN_DATA_PATH: Final[str] = "runs/a"
if not os.path.exists(RUN_DATA_PATH):
    os.makedirs(RUN_DATA_PATH)


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
        reactions[aid] = True
    return reactions


def get_action_cost(action: str) -> int:
    return 5


def main():
    rl_debt_collection.run(
        data_path=RUN_DATA_PATH,
        end_date=20260501,
        new_clients_count=2,
        choose_actions_func=choose_actions,
        simulate_reactions_func=simulate_reactions,
        start_date=20240501,
        overwrite=True,
        generator=None,
    )
    revenue = summary.calculate_revenue(RUN_DATA_PATH, None, None)
    cost = summary.calculate_cost(RUN_DATA_PATH, None, None, get_action_cost)
    print(f"revenue:  {revenue}, cost: {cost}, profit: {revenue - cost}")


if __name__ == "__main__":
    main()
