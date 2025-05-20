import os
from typing import Final

import pandas as pd
from abt import load_or_create_table
from clients_code import Client
import datetime
import numpy as np

from tables_types import ClientsRow

TEST_DATA_PATH: Final[str] = os.path.join(os.path.dirname(__file__), "test_data")


def test_get_starter(benchmark):
    client: Client = benchmark(
        Client.get_starter,
        "2024010100001",
        np.random.default_rng(),
        2,
        datetime.datetime(2024, 1, 23),
    )
    assert client.cid == "2024010100001"
    assert client.year == 2024


def test_simulate_next_year(benchmark):
    client: Client = Client.get_starter(
        "2024010100001",
        np.random.default_rng(),
        2,
        datetime.datetime(2024, 1, 23),
    )
    benchmark(client.simulate_next_year, np.random.default_rng())
    assert client.year != 2024


def test_get_list_from_dataframe(benchmark):
    clients_df: pd.DataFrame = load_or_create_table(
        os.path.join(TEST_DATA_PATH, "tables"), "clients", ClientsRow, False
    )
    clients = benchmark(Client.get_list_from_dataframe, clients_df)
    assert len(clients) == len(clients_df)
