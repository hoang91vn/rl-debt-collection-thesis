import pandas as pd
from typing import Dict, List, Union, Final
from other.special_types import (
    TransactionsData,
    AccountPeriodInfo,
    AccountHistory,
    CidAid,
)
import os
import pickle

EXCLUDED_ABT_COLUMNS: Final[List[str]] = ["cid", "aid", "period"]


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


def get_previous_period(period: str) -> str:
    """
    Takes period in format yyyymm and returns previous period in format yyyymm.
    """
    year = int(period[:4])
    month = int(period[4:])
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    return f"{year}{month:02d}"


def get_all_cidaids(transactions: pd.DataFrame, period: str) -> List[CidAid]:
    """
    Returns a list of dictionaries with all "cid" and "aid" for the transactions in the given period.
    """
    transactions_tmp = transactions[transactions["period"].astype(str) == period]
    cidaids: List[CidAid] = []
    for _, row in transactions_tmp.iterrows():
        cidaids.append({"cid": row["cid"], "aid": row["aid"]})
    return cidaids


def get_transactions_data(
    transactions: pd.DataFrame, aid: str, period: str
) -> TransactionsData | None:
    """
    Returns a dictionary for the transactions for given aid and period with the following keys:
    - paid_installments: int
    - due_installments: int
    - status: str
    - coll_status: str
    - pay_days: int
    """
    transactions_tmp = transactions[
        (transactions["aid"] == aid) & (transactions["period"] == period)
    ]
    if transactions_tmp.empty:
        return None
    return {
        "paid_installments": transactions_tmp["paid_installments"].iloc[0],
        "due_installments": transactions_tmp["due_installments"].iloc[0],
        "status": transactions_tmp["status"].iloc[0],
        "coll_status": transactions_tmp["coll_status"].iloc[0],
        "pay_days": transactions_tmp["pay_days"].iloc[0],
    }


def get_collection_actions(
    collection_actions: pd.DataFrame, aid: str, period: str
) -> Union[str, None]:
    """
    Returns a string of actions for the given aid and period. If there are no actions, returns None.
    """
    action: str = ""
    collection_actions_tmp = collection_actions[
        (collection_actions["aid"] == aid) & (collection_actions["period"] == period)
    ]
    for _, row in collection_actions_tmp.iterrows():
        action = f"{(str(int(row['action'])))}{action}"
    if action == "":
        return None
    return action


def get_account_period_info(
    abt: pd.DataFrame,
    transactions: pd.DataFrame,
    collection_actions: pd.DataFrame,
    cid: str,
    aid: str,
    period: str,
    included_abt_columns: List[str] | None = None,
    excluded_abt_columns: List[str] = EXCLUDED_ABT_COLUMNS,
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
    abt_tmp = abt.loc[abt["aid"] == aid]
    if abt_tmp.empty:
        observation = None
    else:
        if included_abt_columns is not None:
            abt_tmp = abt_tmp[included_abt_columns]
        abt_tmp = abt_tmp.drop(columns=excluded_abt_columns, errors="ignore")
        observation = abt_tmp.iloc[0]
    status_data = get_transactions_data(transactions, aid, period)
    if status_data is None:
        return None
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
    sas_data_path: str,
    included_abt_columns: List[str] | None = None,
) -> Dict[str, AccountHistory]:
    """
    Returns a dictionary of all accounts histories where the key is the aid and the value is a dictionary with the following keys
    - history: List[AccountTwoPeriodInfo]
    - terminated: bool
    """
    # aid should be the key of the dictionary
    accounts_histories: Dict[str, AccountHistory] = {}
    transactions = pd.read_sas(
        f"{sas_data_path}\\transactions.sas7bdat", format="sas7bdat", encoding="utf-8"
    )
    collection_actions = pd.read_sas(
        f"{sas_data_path}\\collection_actions.sas7bdat",
        format="sas7bdat",
        encoding="utf-8",
    )
    all_periods: List[str] = transactions["period"].unique().astype(str).tolist()
    for period in all_periods:
        print("period:", period)
        all_cidaids = get_all_cidaids(transactions, period)
        previous_abt = None
        try:
            previous_abt = pd.read_sas(
                f"{sas_data_path}\\abt_{get_previous_period(period)}.sas7bdat",
                format="sas7bdat",
                encoding="utf-8",
            )
            if previous_abt is None:
                print(f"File abt_{get_previous_period(period)}.sas7bdat is empty")
        except FileNotFoundError:
            print(f"File abt_{get_previous_period(period)}.sas7bdat not found")
        try:
            current_abt = pd.read_sas(
                f"{sas_data_path}\\abt_{period}.sas7bdat",
                format="sas7bdat",
                encoding="utf-8",
            )
        except FileNotFoundError:
            print(f"File abt_{period}.sas7bdat not found")
            raise FileNotFoundError
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
            if current_info["transactions_data"]["status"] != "A":
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
