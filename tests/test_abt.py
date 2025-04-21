import pytest
import datetime
import os
from typing import Final
from old_sas.abt import (
    run,
    generate_new_clients_accounts_transactions,
    make_production_df,
    simulate_actions_and_responses,
    load_table,
    simulate_next_year_for_clients,
    make_abt_base,
    make_summary_abt,
)
from old_sas.tables_types import (
    ClientsRow,
    AccountsRow,
    TransactionsRow,
    CollectionActionsRow,
)
import numpy as np
import pandas as pd

TEST_DATA_PATH: Final[str] = os.path.join(os.path.dirname(__file__), "test_data")


@pytest.mark.skip(
    reason="This test is skipped because it is not relevant to the current context."
)
def test_run(benchmark):
    data_path: str = os.path.join(
        os.path.dirname(__file__), "test_data", "simulate", "data"
    )
    generator: np.random.Generator = np.random.default_rng(42)
    benchmark.pedantic(
        run,
        args=(),
        kwargs={
            "data_path": data_path,
            "start_date": 20000101,
            "end_date": 20020101,
            "new_clients_count": 1,
            "new_accounts_count": 1,
            "generator": generator,
            "overwrite": True,
        },
        iterations=1,
    )


def test_make_production_df(benchmark):
    clients_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "clients", ClientsRow, False
    )
    accounts_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "accounts", AccountsRow, False
    )
    production_df = benchmark(make_production_df, clients_df, accounts_df)
    assert len(production_df) == len(accounts_df)


def test_make_abt_base(benchmark):
    clients_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "clients", ClientsRow, False
    )
    accounts_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "accounts", AccountsRow, False
    )
    transactions_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "transactions", TransactionsRow, False
    )
    production_df: pd.DataFrame = make_production_df(clients_df, accounts_df)
    last_period: int = transactions_df["period"].max()
    abt_base_df = benchmark(make_abt_base, production_df, transactions_df, last_period)
    assert len(abt_base_df) > 0


def test_make_summary_abt(benchmark):
    abt_path: str = os.path.join(TEST_DATA_PATH, "abts")
    # find in the abt_path the file with the name "abt_base_{period}.csv"  where period is the highest number
    periods = [
        f.split("_")[2].split(".")[0]
        for f in os.listdir(abt_path)
        if f.startswith("abt_base_") and f.endswith(".csv")
    ]
    highest_period = max(int(p) for p in periods)
    last_abt_df = pd.read_csv(os.path.join(abt_path, f"abt_base_{highest_period}.csv"))

    summary_abt_df = benchmark(make_summary_abt, highest_period, abt_path)
    assert len(summary_abt_df) == len(last_abt_df)


def test_simulate_actions_and_responses(benchmark):
    collection_actions_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"),
        "collection_actions",
        CollectionActionsRow,
        False,
    )
    summary_abt_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "summary_abt_202604", None, False
    )
    new_transactions_df, new_collection_actions_df = benchmark(
        simulate_actions_and_responses,
        np.random.default_rng(),
        summary_abt_df,
        collection_actions_df,
        202604,
    )
    assert len(new_transactions_df) == len(summary_abt_df)
    assert len(new_collection_actions_df) != 0


def test_generate_new_clients_accounts_transactions(benchmark):
    generator: np.random.Generator = np.random.default_rng(42)
    new_clients, new_accounts, new_transactions = benchmark(
        generate_new_clients_accounts_transactions,
        generator,
        2,
        datetime.datetime.now(),
        1,
    )
    assert len(new_clients) == 2
    assert len(new_accounts) == 2
    assert len(new_transactions) == 2


def test_simulate_next_year_for_clients(benchmark):
    clients_df: pd.DataFrame = load_table(
        os.path.join(TEST_DATA_PATH, "tables"), "clients", ClientsRow, False
    )
    new_clients_df = benchmark(
        simulate_next_year_for_clients,
        clients_df,
    )
    assert len(new_clients_df) == len(clients_df)
