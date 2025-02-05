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
        "transactions_data": TransactionsData | None,
        "action": str | None,
    },
)

AccountTwoPeriodInfo = TypedDict(
    "AccountTwoPeriodInfo",
    {
        "cid": str,
        "aid": str,
        "previous": AccountPeriodInfo,
        "current": AccountPeriodInfo,
    },
)

CidAid = TypedDict(
    "CidAid",
    {
        "cid": str,
        "aid": str,
    },
)


CollectionActionRow = TypedDict(
    "CollectionActionRow",
    {
        "cid": str,
        "aid": str,
        "period": str,
        "action_nr": int,
        "action": int,
        "coll_status": str,
    },
)

AccountHistory = TypedDict(
    "AccountHistory", {"history": List[AccountTwoPeriodInfo], "terminated": bool}
)


Transition = tuple[pd.Series, str, float, pd.Series | None]
Episode = List[Transition]
