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
        index_col=["period", "aid"],
    )
    accounts_df = load_table(data_path, "accounts", AccountsRow, False, index_col="aid")
    if start_period is None:
        start_period = int(transactions_df.index.get_level_values("period").min())
    if end_period is None:
        end_period = int(transactions_df.index.get_level_values("period").max())
    total_revenue: int = 0
    for row in transactions_df.loc[(start_period,) : (end_period,)].itertuples(True):
        current_period_paid_installments: int = getattr(row, "paid_installments")
        new_paid_installments: int = 0
        aid: str = getattr(row, "Index")[1]
        period: int = int(getattr(row, "Index")[0])
        try:
            last_period_paid_installments = int(
                transactions_df.at[
                    (get_relative_period(period, -1), aid),
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
    for row in collection_actions_df[
        (collection_actions_df["period"] >= start_period)
        & (collection_actions_df["period"] <= end_period)
    ].itertuples():
        total_cost += get_action_cost(getattr(row, "action"))
    return total_cost


def calculate_period_cost(
    data_path: str,
    period: int,
    get_action_cost: Callable[[str], int],
) -> int:
    return calculate_cost(data_path, period, period, get_action_cost)


def calculate_period_revenue(data_path: str, period: int) -> int:
    return calculate_revenue(data_path, period, period)
