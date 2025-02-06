from typing import Dict, List, Final
import pandas as pd
from special_types import (
    AccountHistory,
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
    aids_to_decide: List[str],
    accounts_histories: Dict[str, AccountHistory],
) -> Dict[str, str]:
    decisions: Dict[str, str] = {}
    for aid in aids_to_decide:
        decisions[aid] = np.random.choice(ACTIONS)
    return decisions
