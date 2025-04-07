from typing import List, TypedDict
import numpy as np
import pandas as pd
from tables_types import (
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
import os
import datetime

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
        coll_status=CollStat.AMICABLE,
        due_installments=0,
        paid_installments=0,
        pay_days=0,
    )


def get_next_period(period: int) -> int:
    # format is YYYYmm
    year: int = period // 100
    month: int = period % 100
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
    return year * 100 + month


def get_relative_period(period: int, month_change: int) -> int:
    year: int = period // 100
    month: int = period % 100
    month += month_change
    while month > 12:
        year += 1
        month -= 12
    while month < 1:
        year -= 1
        month += 12
    return year * 100 + month


def get_period_datetime(period: int) -> datetime.datetime:
    year: int = period // 100
    month: int = period % 100
    return datetime.datetime(year, month, 1)


def is_last_day_of_month(date: datetime.datetime) -> bool:
    return (date + datetime.timedelta(days=1)).day == 1


def simulate_period(
    data_path: str,
    start_period: int,
    end_period: int,
    new_clients_count: int,
    new_accounts_count: int,
    generator: np.random.Generator,
) -> None:
    # load clients
    clients_path: str = os.path.join(data_path, "clients.csv")
    clients_df = pd.read_csv(clients_path, dtype=ClientsRow)
    # load accounts
    accounts_path: str = os.path.join(data_path, "accounts.csv")
    accounts_df = pd.read_csv(accounts_path, dtype=AccountsRow)
    # load transactions
    transactions_path: str = os.path.join(data_path, "transactions.csv")
    transactions_df = pd.read_csv(transactions_path, dtype=TransactionsRow)
    last_aid: str = accounts_df["aid"].max()
    start_period_datetime: datetime.datetime = get_period_datetime(start_period)
    end_period_datetime: datetime.datetime = get_period_datetime(end_period)
    # generate new clients
    if clients_df.empty:
        next_cid: int = 1
    else:
        next_cid: int = int(clients_df["cid"].max()) + 1
    current_date: datetime.datetime = start_period_datetime
    new_clients: List[Client] = []
    while current_date <= end_period_datetime:
        current_period: int = current_date.year * 100 + current_date.month
        for _ in range(new_clients_count):
            cid: str = str(next_cid).zfill(10)
            client: Client = Client.get_starter(
                cid, generator, 2, current_date=current_date
            )
            new_clients.append(client)
            next_cid += 1
        # check if last day of the month
        if is_last_day_of_month(current_date):
            # add new clients to the dataframe
            new_clients_df: pd.DataFrame = pd.DataFrame(
                [client.to_dict() for client in new_clients]
            )
            clients_df = pd.concat([clients_df, new_clients_df], ignore_index=True)
            new_clients = []
            pass
        # Perform operations for the current period if needed
        current_date += datetime.timedelta(days=1)
    # generate new accounts

    # save clients
    clients_df.to_csv(clients_path, index=False)
    # save accounts
    accounts_df.to_csv(accounts_path, index=False)
    # save transactions
    transactions_df.to_csv(transactions_path, index=False)
