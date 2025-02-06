from typing import TypedDict, List
import pandas as pd


TransactionsData = TypedDict(
    "TransactionsData",
    {
        "paid_installments": int,
        "due_installments": int,
        "status": str,
        "coll_status": str,
        "pay_days": int,
    },
)

AccountPeriodInfo = TypedDict(
    "AccountPeriodInfo",
    {
        "cid": str,
        "aid": str,
        "period": str,
        "abt_data": pd.Series | None,
        "transactions_data": TransactionsData,
        "action": str | None,
    },
)

CidAid = TypedDict(
    "CidAid",
    {
        "cid": str,
        "aid": str,
    },
)

AccountHistory = TypedDict(
    "AccountHistory", {"history": List[AccountPeriodInfo], "terminated": bool}
)
