from enum import Enum
import json
import math
from typing import Any, Dict, List, Tuple, TypedDict, cast
import numpy as np
import pandas as pd
from tables_types import (
    CollectionActionsRow,
    TransactionsRow,
    ClientsRow,
    AbtBaseRow,
    ProductionRow,
    AccountsRow,
)
from dictionaries import (
    Branch,
    Gender,
    JobCode,
    MaritalStatus,
    City,
    Homes,
    Cars,
    CollStat,
    Status,
)
from clients_code import Client, Account
from abt_behavioral_columns import (
    make_abt_base,
    make_production_df,
    make_summary_abt,
)
from util import get_month_period_difference, get_relative_period, get_type
import os
import datetime
import logging

# fmt: off
data_mat = np.array([
    [0.850, 0.150, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.250, 0.600, 0.150, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.040, 0.220, 0.200, 0.540, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.005, 0.020, 0.081, 0.102, 0.792, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.010, 0.080, 0.090, 0.820, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.020, 0.030, 0.940]
])
data_mat_positive = np.array([
    [0.800, 0.200, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.250, 0.850, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.050, 0.750, 0.200, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.005, 0.025, 0.080, 0.890, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.012, 0.088, 0.900, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000, 0.000],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.010, 0.090, 0.900, 0.000]
])
# fmt: on


def get_first_transaction_row(cid: str, aid: str, period: int) -> TransactionsRow:
    return TransactionsRow(
        cid=cid,
        aid=aid,
        period=period,
        fin_period=period,
        status=Status.A,
        coll_status=CollStat.GOOD_PAYER,
        due_installments=0,
        paid_installments=0,
        pay_days=0,
    )


def get_period(date: datetime.datetime) -> int:
    """
    >>> get_period(datetime.datetime(2024, 7, 29))
    202407
    """
    return date.year * 100 + date.month


def get_next_period(period: int) -> int:
    """
    >>> get_next_period(202412)
    202501
    """
    return get_relative_period(period, 1)


def get_period_datetime(period: int) -> datetime.datetime:
    """
    >>> get_period_datetime(202401)
    datetime.datetime(2024, 1, 1, 0, 0)
    """
    year: int = period // 100
    month: int = period % 100
    return datetime.datetime(year, month, 1)


def get_date_datetime(date: int) -> datetime.datetime:
    """
    >>> get_date_datetime(20240101)
    datetime.datetime(2024, 1, 1, 0, 0)
    """
    # YYYYMMDD
    year: int = date // 10000
    month: int = (date // 100) % 100
    day: int = date % 100
    return datetime.datetime(year, month, day)


def get_date_int(date: datetime.datetime) -> int:
    return date.year * 10000 + date.month * 100 + date.day


def is_last_day_of_month(date: datetime.datetime) -> bool:
    return (date + datetime.timedelta(days=1)).day == 1


def is_last_day_of_year(date: datetime.datetime) -> bool:
    return date.month == 12 and date.day == 31


def generate_aid(date: datetime.datetime, type: str, account_in_day: int) -> str:
    """
    >>> generate_aid(datetime.datetime(2024, 9, 27), "ins", 112)
    'ins202409270112'
    """
    year: int = date.year
    month: int = date.month
    day: int = date.day
    aid: str = f"{type}{year}{month:02d}{day:02d}{account_in_day:04d}"
    return aid


def run(
    data_path: str,
    end_date: int,
    new_clients_count: int,
    new_accounts_count: int,
    generator: np.random.Generator,
    start_date: int = 0,
    overwrite: bool = False,
) -> None:
    if start_date == 0:
        metadata_path: str = os.path.join(data_path, "metadata.json")
        try:
            # read json
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                # YYYYMMDD
                start_date_str: str = metadata["current_date"]
                start_date = int(start_date_str)
            start_date = metadata["current_date"]
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Metadata file not found in {data_path}. Please provide a valid current_date."
            )
    if overwrite:
        # remove all files in data_path
        for file in os.listdir(data_path):
            file_path: str = os.path.join(data_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    simulate(
        data_path,
        start_date,
        end_date,
        new_clients_count,
        new_accounts_count,
        generator=generator,
    )


def choose_action() -> str:
    return "1"


def calculate_positive_reaction(action: str, generator: np.random.Generator) -> bool:
    return generator.random() < 0.5


def get_new_coll_status(due_installments: int, coll_status: CollStat) -> CollStat:
    if coll_status in [CollStat.GOOD_PAYER, CollStat.CURED] and due_installments == 1:
        coll_status = CollStat.AMICABLE
    elif coll_status == CollStat.AMICABLE and due_installments == 4:
        coll_status = CollStat.PRE_LEGAL
    elif coll_status == CollStat.PRE_LEGAL and due_installments == 5:
        coll_status = CollStat.LEGAL
    elif coll_status == CollStat.LEGAL and due_installments == 7:
        coll_status = CollStat.EXECUTION
    elif coll_status == CollStat.EXECUTION and due_installments == 10:
        coll_status = CollStat.POST_EXECUTION
    elif coll_status != CollStat.GOOD_PAYER and due_installments == 0:
        coll_status = CollStat.CURED
    if due_installments == 12:
        coll_status = CollStat.WRITE_OFF
    return coll_status


def load_table(
    data_path: str,
    table_name: str,
    row_type: type | None,
    create_if_not_exist: bool = True,
) -> pd.DataFrame:
    table_path: str = os.path.join(data_path, f"{table_name}.csv")
    try:
        table_df = pd.read_csv(
            table_path, dtype=get_type(row_type) if row_type else None
        )
    except FileNotFoundError:
        if not create_if_not_exist:
            raise FileNotFoundError(f"Table {table_name} not found in {data_path}.")
        table_df = pd.DataFrame(columns=list(row_type.__annotations__.keys()))
    return table_df


def save_table(
    data_path: str,
    table_name: str,
    table_df: pd.DataFrame,
) -> None:
    table_path: str = os.path.join(data_path, f"{table_name}.csv")
    table_df.to_csv(table_path, index=False)


def save_metadata(data_path: str, current_date: datetime.datetime) -> None:
    metadata_path: str = os.path.join(data_path, "metadata.json")
    metadata = {
        "current_date": get_date_int(current_date),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    logging.info(f"Metadata saved to {metadata_path}")


def generate_new_clients_accounts_transactions(
    generator: np.random.Generator,
    new_clients_count: int,
    current_date: datetime.datetime,
    next_cid: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    new_clients: List[Client] = []
    new_accounts: List[Account] = []
    new_transactions: List[TransactionsRow] = []
    for new_client_index in range(new_clients_count):
        cid: str = str(next_cid).zfill(10)
        client: Client = Client.get_starter(
            cid, generator, 2, current_date=current_date
        )
        new_clients.append(client)
        next_cid += 1
        aid: str = generate_aid(current_date, "ins", new_client_index + 1)
        account: Account = Account.generate_account(
            client, aid, current_date, generator
        )
        new_accounts.append(account)
        new_transaction: TransactionsRow = get_first_transaction_row(
            client.cid, aid, get_period(current_date)
        )
        new_transactions.append(new_transaction)
    new_clients_df: pd.DataFrame = pd.DataFrame(
        [client.to_dict() for client in new_clients]
    )
    new_accounts_df: pd.DataFrame = pd.DataFrame(
        [account.to_dict() for account in new_accounts]
    )
    new_transactions_df: pd.DataFrame = pd.DataFrame(
        [transaction for transaction in new_transactions]
    )
    return new_clients_df, new_accounts_df, new_transactions_df


def get_next_cid(clients_df: pd.DataFrame) -> int:
    if clients_df.empty:
        return 1
    else:
        return int(clients_df["cid"].max()) + 1


def simulate_actions_and_responses(
    generator: np.random.Generator,
    summary_abt_df: pd.DataFrame,
    collection_actions_df: pd.DataFrame,
    current_period: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    next_period: int = get_next_period(current_period)
    new_transactions: List[TransactionsRow] = []
    new_collection_actions: List[CollectionActionsRow] = []
    last_actions_current_period_df = collection_actions_df.loc[
        collection_actions_df["period"] == current_period
    ]
    last_actions: Dict[str, str] = (
        last_actions_current_period_df.groupby(["aid"])["action"]
        .last()  # or .iloc[-1] if you need something else
        .to_dict()
    )
    counts_array: np.ndarray = np.zeros(13, dtype=int)
    stat: pd.DataFrame = (
        summary_abt_df[["act_due", "score"]].groupby("act_due").agg({"score": "count"})
    )
    for i in range(0, 13):
        if i in stat.index:
            counts_array[i] = stat.loc[i, "score"]
    print(counts_array)

    for act_due_group_value, act_due_group in summary_abt_df.sort_values(
        by=["act_due", "score"], ascending=[True, False]
    ).groupby("act_due"):
        act_due_group_value = cast(int, act_due_group_value)
        ob: int = 0
        positive_reaction_sums = np.zeros(13, dtype=int)
        negative_reaction_sums = np.zeros(13, dtype=int)
        for i in range(0, 13):
            positive_reaction_sums[i] = (
                data_mat_positive[act_due_group_value, 0:i].sum()
                * counts_array[act_due_group_value]
            )
            negative_reaction_sums[i] = (
                data_mat[act_due_group_value, 0:i].sum()
                * counts_array[act_due_group_value]
            )
        for _, summary_row in act_due_group.iterrows():
            ob += 1
            if summary_row["aid"] in last_actions:
                last_action: str = last_actions[summary_row["aid"]]
            else:
                last_action: str = "0"
            is_reaction_positive: bool = calculate_positive_reaction(
                last_action, generator
            )
            # appropriate_matrix = (
            #     data_mat_positive if is_reaction_positive else data_mat
            # )
            appropriate_sums = (
                positive_reaction_sums
                if is_reaction_positive
                else negative_reaction_sums
            )
            act_due: int = summary_row["act_due"]
            act_paid: int = summary_row["act_paid_installments"]

            new_due_installments: int = act_due
            new_paid_installments: int = act_paid
            total_due_for_next_period: int = np.min(
                [
                    get_month_period_difference(
                        int(summary_row["fin_period"]), next_period
                    ),
                    summary_row["app_n_installments"],
                ]
            )
            new_status: Status = summary_row["status"]
            pay_days: int = 0
            if 0 <= act_due < 12:
                i = next(
                    (i for i in range(12, -1, -1) if ob > appropriate_sums[i]),
                    None,
                )
                if i is not None:
                    new_due_installments = np.max(
                        [
                            np.min(
                                [
                                    i,
                                    total_due_for_next_period - act_paid,
                                ]
                            ),
                            0,
                        ]
                    )
                    new_paid_installments = (
                        total_due_for_next_period - new_due_installments
                    )
                    if new_paid_installments == act_paid:
                        # No payment
                        pay_days = 0
                    else:
                        # Payment
                        if summary_row["act_due"] < 2:
                            pay_days = -int(15 * abs(generator.normal(0, 1)) / 4)
                        else:
                            pay_days = int(15 * generator.normal(0, 1) / 4)
            if new_paid_installments == summary_row["app_n_installments"]:
                new_due_installments = 0
                new_status = Status.C
            elif new_due_installments == 12:
                new_status = Status.B

            new_coll_status = get_new_coll_status(
                new_due_installments, summary_row["coll_status"]
            )

            new_transaction: TransactionsRow = TransactionsRow(
                aid=summary_row["aid"],
                cid=summary_row["cid"],
                period=get_next_period(current_period),
                fin_period=summary_row["fin_period"],
                status=new_status,
                coll_status=new_coll_status,
                due_installments=new_due_installments,
                paid_installments=new_paid_installments,
                pay_days=pay_days,
            )
            new_transactions.append(new_transaction)

            if new_transaction["status"] == Status.A:
                # choose action
                action: str = choose_action()
                collection_action: CollectionActionsRow = CollectionActionsRow(
                    action=action,
                    cid=summary_row["cid"],
                    aid=summary_row["aid"],
                    period=get_next_period(current_period),
                    coll_status=new_transaction["coll_status"],
                )
                new_collection_actions.append(collection_action)
    # add new collection actions to dataframe
    new_collection_actions_df: pd.DataFrame = pd.DataFrame(
        [action for action in new_collection_actions]
    )
    # add new transactions to dataframe
    new_transactions_df: pd.DataFrame = pd.DataFrame(
        [transaction for transaction in new_transactions]
    )

    return new_transactions_df, new_collection_actions_df


def simulate_next_year_for_clients(
    clients_df: pd.DataFrame,
) -> pd.DataFrame:
    clients = Client.get_list_from_dataframe(clients_df)
    for client in clients:
        client.simulate_next_year(generator=np.random.default_rng())
    clients_df = pd.DataFrame(
        [client.to_dict() for client in clients], columns=clients_df.columns
    )
    return clients_df


def simulate(
    data_path: str,
    start_date: int,
    end_date: int,
    new_clients_count: int,
    new_accounts_count: int,
    generator: np.random.Generator,
) -> None:
    # load tables
    clients_df: pd.DataFrame = load_table(data_path, "clients", ClientsRow)
    accounts_df: pd.DataFrame = load_table(data_path, "accounts", AccountsRow)
    transactions_df: pd.DataFrame = load_table(
        data_path, "transactions", TransactionsRow
    )
    collection_actions_df: pd.DataFrame = load_table(
        data_path, "collection_actions", CollectionActionsRow
    )
    start_date_datetime: datetime.datetime = get_date_datetime(start_date)
    end_date_datetime: datetime.datetime = get_date_datetime(end_date)
    current_date: datetime.datetime = start_date_datetime
    while current_date < end_date_datetime:
        current_period: int = get_period(current_date)
        new_clients_df, new_accounts_df, new_transactions_df = (
            generate_new_clients_accounts_transactions(
                generator,
                new_clients_count,
                current_date,
                get_next_cid(clients_df),
            )
        )
        clients_df = pd.concat(
            [clients_df, new_clients_df], ignore_index=True, copy=False
        )
        accounts_df = pd.concat(
            [accounts_df, new_accounts_df], ignore_index=True, copy=False
        )
        transactions_df = pd.concat(
            [transactions_df, new_transactions_df], ignore_index=True, copy=False
        )
        if is_last_day_of_month(current_date):
            production_df: pd.DataFrame = make_production_df(clients_df, accounts_df)
            abt_base_current_period_df: pd.DataFrame = make_abt_base(
                production_df, transactions_df, current_period
            )
            save_table(
                data_path,
                f"abt_base_{current_period}",
                abt_base_current_period_df,
            )
            summary_abt_df: pd.DataFrame = make_summary_abt(current_period, data_path)
            save_table(
                data_path,
                f"summary_abt_{current_period}",
                summary_abt_df,
            )
            new_transactions_df, new_collection_actions_df = (
                simulate_actions_and_responses(
                    generator,
                    summary_abt_df,
                    collection_actions_df,
                    current_period,
                )
            )
            transactions_df = pd.concat(
                [transactions_df, new_transactions_df], ignore_index=True, copy=False
            )
            collection_actions_df = pd.concat(
                [collection_actions_df, new_collection_actions_df],
                ignore_index=True,
                copy=False,
            )
        if is_last_day_of_year(current_date):
            clients_df = simulate_next_year_for_clients(clients_df)

        current_date += datetime.timedelta(days=1)

    # save tables
    save_table(data_path, "clients", clients_df)
    save_table(data_path, "accounts", accounts_df)
    save_table(data_path, "transactions", transactions_df)
    save_table(data_path, "collection_actions", collection_actions_df)
    save_metadata(data_path, current_date)
