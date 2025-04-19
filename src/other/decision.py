from typing import Dict, List
from other.special_types import (
    AccountHistory,
)
import numpy as np
from other.environment import ACTIONS


def decide_for_all(
    aids_to_decide: List[str],
    accounts_histories: Dict[str, AccountHistory],
) -> Dict[str, str]:
    decisions: Dict[str, str] = {}
    for aid in aids_to_decide:
        decisions[aid] = np.random.choice(ACTIONS)
    return decisions
