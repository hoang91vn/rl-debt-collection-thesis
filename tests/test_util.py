import os
from typing import Dict, Final
from special_types import AccountHistory
from util import get_all_accounts_histories

TEST_DATA_PATH: Final[str] = os.path.join(os.path.dirname(__file__), "test_data")


def test_get_all_accounts_histories(benchmark):
    accounts_histories: Dict[str, AccountHistory] = benchmark(
        get_all_accounts_histories, os.path.join(TEST_DATA_PATH, "simulate/data")
    )
    terminated_histories_count = len(
        [
            (key, history)
            for (key, history) in accounts_histories.items()
            if history["terminated"]
        ]
    )
    active_histories_count = (
        len(accounts_histories.items()) - terminated_histories_count
    )
    assert len(accounts_histories.items()) == 731
    assert terminated_histories_count == 154
    assert active_histories_count == 577
