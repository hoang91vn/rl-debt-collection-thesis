from enum import Enum
import pandas as pd
from typing import Any, Dict, List, Union, Final, cast
import os
import pickle
from special_types import (
    TransactionsData,
    AccountPeriodInfo,
    AccountHistory,
    CidAid,
)
from tables_types import AccountsRow, ClientsRow, CollectionActionsRow, TransactionsRow
from dictionaries import Status, CollStat


def get_relative_period(period: int, month_change: int) -> int:
    """
    >>> get_relative_period(202412, 15)
    202603
    """
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


def get_month_period_difference(period1: int, period2: int) -> int:
    """
    Returns the number of months between two periods in format yyyymm.
    >>> get_month_period_difference(202401, 202809)
    56
    """
    year1: int = period1 // 100
    month1: int = period1 % 100
    year2: int = period2 // 100
    month2: int = period2 % 100
    return (year2 - year1) * 12 + (month2 - month1)


def get_type(type_to_digest: type) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    for key, value in type_to_digest.__annotations__.items():
        if issubclass(value, Enum):
            mapping[key] = value._member_type_  # type: ignore
        else:
            mapping[key] = value
    return mapping


def create_table(
    row_type: type | None,
    index_col: str | List[str] | None = None,
    initial_data: Dict[str, Any] | List[Any] | None = None,
) -> pd.DataFrame:
    table_df = pd.DataFrame(
        columns=list(row_type.__annotations__.keys()), data=initial_data
    )
    if index_col is not None:
        table_df.set_index(index_col, inplace=True)
    return table_df


def load_or_create_table(
    data_path: str | None,
    table_name: str | None,
    row_type: type | None,
    create_if_not_exist: bool = True,
    index_col: str | List[str] | None = None,
) -> pd.DataFrame:
    if data_path is not None and table_name is not None:
        table_path: str = os.path.join(data_path, f"{table_name}.csv")
        try:
            table_df = pd.read_csv(
                table_path,
                dtype=get_type(row_type) if row_type else None,
                index_col=index_col,
            )
        except FileNotFoundError:
            if not create_if_not_exist:
                raise FileNotFoundError(f"Table {table_name} not found in {data_path}.")
            table_df = create_table(row_type, index_col)
    else:
        table_df = create_table(row_type, index_col)
    return table_df


def save_table(
    data_path: str, table_name: str, table_df: pd.DataFrame, index: bool = True
) -> None:
    table_path: str = os.path.join(data_path, f"{table_name}.csv")
    table_df.to_csv(table_path, index=index)


def load_collection_actions_table(
    data_path: str, create_if_not_exist: bool = False
) -> pd.DataFrame:
    return load_or_create_table(
        data_path,
        "collection_actions",
        CollectionActionsRow,
        create_if_not_exist,
        ["period", "aid"],
    )


def load_accounts_table(
    data_path: str, create_if_not_exist: bool = False
) -> pd.DataFrame:
    return load_or_create_table(
        data_path, "accounts", AccountsRow, create_if_not_exist, "aid"
    )


def load_clients_table(
    data_path: str, create_if_not_exist: bool = False
) -> pd.DataFrame:
    return load_or_create_table(
        data_path, "clients", ClientsRow, create_if_not_exist, "cid"
    )


def load_transactions_table(
    data_path: str, create_if_not_exist: bool = False
) -> pd.DataFrame:
    return load_or_create_table(
        data_path,
        "transactions",
        TransactionsRow,
        create_if_not_exist,
        ["period", "aid"],
    )


def load_abt_summary_table(
    data_path: str, period: int, create_if_not_exist: bool = False
) -> pd.DataFrame:
    return load_or_create_table(
        data_path, f"summary_abt_{period}", None, create_if_not_exist, "aid"
    )


def load_abt_base_table(
    data_path: str, period: int, create_if_not_exist: bool = False
) -> pd.DataFrame:
    return load_or_create_table(
        data_path, f"abt_base_{period}", None, create_if_not_exist, ["period", "aid"]
    )


def get_period_range(start_period: int, end_period: int) -> List[int]:
    period_range: List[int] = []
    current_period: int = start_period
    while current_period <= end_period:
        period_range.append(current_period)
        current_period = get_relative_period(current_period, 1)
    return period_range


def get_all_cidaids(transactions: pd.DataFrame, period: int) -> List[CidAid]:
    """
    Returns a list of dictionaries with all "cid" and "aid" for the transactions in the given period.
    """
    transactions_tmp = transactions.loc[(period,), :]
    cidaids: List[CidAid] = []
    for row in transactions_tmp.itertuples(True):
        cidaids.append({"cid": getattr(row, "cid"), "aid": getattr(row, "Index")})
    return cidaids


def get_transactions_data(
    transactions: pd.DataFrame, aid: str, period: int
) -> TransactionsData | None:
    """
    Returns a dictionary for the transactions for given aid and period with the following keys:
    - paid_installments: int
    - due_installments: int
    - status: str
    - coll_status: str
    - pay_days: int
    """
    try:
        row = cast(pd.Series, transactions.loc[(period, aid)])
        return {
            "paid_installments": row["paid_installments"],
            "due_installments": row["due_installments"],
            "status": row["status"],
            "coll_status": row["coll_status"],
            "pay_days": row["pay_days"],
        }
    except KeyError:
        return None


def get_collection_actions(
    collection_actions: pd.DataFrame, aid: str, period: int
) -> Union[str, None]:
    """
    Returns a string of actions for the given aid and period. If there are no actions, returns None.
    """
    try:
        action: str = str(collection_actions.loc[(period, aid), "action"])
    except KeyError:
        return None
    return action


def get_account_period_info(
    abt: pd.DataFrame | None,
    transactions: pd.DataFrame,
    collection_actions: pd.DataFrame | None,
    cid: str,
    aid: str,
    period: int,
    included_abt_columns: List[str] | None = None,
    excluded_abt_columns: List[str] = [],
) -> AccountPeriodInfo | None:
    """
    Returns a dictionary formed from the data from SAS table for a given cid, aid and period with the following keys:
    - cid: str
    - aid: str
    - period: str
    - abt_data: pd.Series
    - transactions_data: TransactionsData
    - action: str | None
    """
    status_data = get_transactions_data(transactions, aid, period)
    if status_data is None:
        return None
    if abt is None:
        observation = None
    else:
        try:
            account_period_row: pd.Series = cast(pd.Series, abt.loc[aid])
            if included_abt_columns is not None:
                account_period_row = account_period_row[included_abt_columns]
            account_period_row = account_period_row.drop(
                columns=excluded_abt_columns, errors="ignore"
            )
            observation = account_period_row
        except KeyError:
            observation = None
    if collection_actions is None:
        action = None
    else:
        action = get_collection_actions(collection_actions, aid, period)
    return {
        "cid": cid,
        "aid": aid,
        "period": period,
        "abt_data": observation,
        "transactions_data": status_data,
        "action": action,
    }


def get_all_accounts_histories(
    data_path: str,
    included_abt_columns: List[str] | None = None,
) -> Dict[str, AccountHistory]:
    """
    Returns a dictionary of all accounts histories where the key is the aid and the value is a dictionary with the following keys
    - history: List[AccountTwoPeriodInfo]
    - terminated: bool
    """
    # aid should be the key of the dictionary
    accounts_histories: Dict[str, AccountHistory] = {}
    transactions = load_transactions_table(data_path)
    collection_actions = load_collection_actions_table(data_path)
    all_periods: List[int] = (
        transactions.index.get_level_values("period").unique().astype(int).tolist()
    )
    for period in all_periods:
        all_cidaids = get_all_cidaids(transactions, period)
        try:
            current_abt = load_abt_summary_table(data_path, period)
        except FileNotFoundError as error:
            print(error)
            current_abt = None
        for cidaids in all_cidaids:
            cid = cidaids["cid"]
            aid = cidaids["aid"]
            if aid not in accounts_histories:
                accounts_histories[aid] = {
                    "history": [],
                    "terminated": False,
                }
            current_info = get_account_period_info(
                current_abt,
                transactions,
                collection_actions,
                cid,
                aid,
                period,
                included_abt_columns=included_abt_columns,
            )
            assert current_info is not None
            if current_info["transactions_data"]["status"] != Status.A:
                accounts_histories[aid]["terminated"] = True
            accounts_histories[aid]["history"].append(current_info)
    return accounts_histories


def save_histories(
    histories: Dict[str, AccountHistory], directory: str, name: str
) -> None:
    """
    Saves the histories to a file of given name in HISTORIES_PATH.
    """
    os.makedirs(directory, exist_ok=True)
    with open(f"{directory}/{name}.pkl", "wb") as f:
        pickle.dump(histories, f)


def load_histories(directory: str, name: str) -> Dict[str, AccountHistory]:
    """
    Loads the histories from a file of given name in HISTORIES_PATH.
    """
    with open(f"{directory}/{name}.pkl", "rb") as f:
        return pickle.load(f)
