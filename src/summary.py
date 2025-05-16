from typing import Callable, cast
import pandas as pd
import numpy as np
import os
from tables_types import AccountsRow, CollectionActionsRow
from util import get_relative_period, load_table, save_table, get_period_range


def calculate_revenue(
    data_path: str, start_period: int | None, end_period: int | None
) -> int:
    transactions_df = load_table(
        data_path,
        "transactions",
        CollectionActionsRow,
        False,
        index_col=["aid", "period"],
    )
    accounts_df = load_table(data_path, "accounts", AccountsRow, False, index_col="aid")
    if start_period is None:
        start_period = int(transactions_df.index.get_level_values("period").min())
    if end_period is None:
        end_period = int(transactions_df.index.get_level_values("period").max())
    total_revenue: int = 0
    for period in get_period_range(start_period, end_period):
        total_revenue += calculate_period_revenue(
            data_path, period, transactions_df, accounts_df
        )
    return total_revenue


def calculate_cost(
    data_path: str,
    start_period: int | None,
    end_period: int | None,
    get_action_cost: Callable[[str], int],
) -> int:
    collection_actions_df = load_table(
        data_path, "collection_actions", CollectionActionsRow, False
    )
    if start_period is None or end_period is None:
        transactions_df: pd.DataFrame = load_table(
            data_path, "transactions", CollectionActionsRow, False
        )
        if start_period is None:
            start_period = int(transactions_df["period"].min())
        if end_period is None:
            end_period = int(transactions_df["period"].max())
    total_cost: int = 0
    for period in get_period_range(start_period, end_period):
        total_cost += calculate_period_cost(
            data_path, period, get_action_cost, collection_actions_df
        )
    return total_cost


def calculate_period_cost(
    data_path: str,
    period: int,
    get_action_cost: Callable[[str], int],
    collection_actions_df: pd.DataFrame | None = None,
) -> int:
    total_cost: int = 0
    if collection_actions_df is None:
        collection_actions_df = load_table(
            data_path, "collection_actions", CollectionActionsRow, False
        )
    for row in collection_actions_df[
        collection_actions_df["period"] == period
    ].itertuples():
        total_cost += get_action_cost(getattr(row, "action"))
    return total_cost


def calculate_period_revenue(
    data_path: str,
    period: int,
    transactions_df: pd.DataFrame | None = None,
    accounts_df: pd.DataFrame | None = None,
) -> int:
    total_revenue: int = 0
    if transactions_df is None:
        transactions_df = load_table(
            data_path,
            "transactions",
            CollectionActionsRow,
            False,
            index_col=["aid", "period"],
        )
    if accounts_df is None:
        accounts_df = load_table(
            data_path, "accounts", AccountsRow, False, index_col="aid"
        )
    for row in transactions_df[
        transactions_df.index.get_level_values("period").astype(np.int64) == period
    ].itertuples(True):
        current_period_paid_installments: int = getattr(row, "paid_installments")
        new_paid_installments: int = 0
        aid: str = getattr(row, "Index")[0]
        try:
            last_period_paid_installments = int(
                transactions_df.at[
                    (aid, get_relative_period(period, -1)),
                    "paid_installments",
                ]
            )
            new_paid_installments: int = (
                current_period_paid_installments - last_period_paid_installments
            )
        except Exception as e:
            new_paid_installments = current_period_paid_installments
        account_installment = int(accounts_df.at[aid, "installment"])
        total_revenue += account_installment * new_paid_installments
    return total_revenue
