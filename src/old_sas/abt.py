from enum import Enum
import json
from typing import Any, Dict, List, TypedDict, cast
import numpy as np
import pandas as pd
from old_sas.tables_types import (
    CollectionActionsRow,
    TransactionsRow,
    ClientsRow,
    AbtBaseRow,
    ProductionRow,
    AccountsRow,
)
from old_sas.dictionaries import (
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
from old_sas.clients_code import Client, Account
from old_sas.abt_behavioral_columns import (
    make_abt_base,
    make_production_df,
    make_summary_abt,
)
from other.util import get_relative_period
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
        coll_status=CollStat.GOOD_PAYER,
        due_installments=0,
        paid_installments=0,
        pay_days=0,
    )


def get_period(date: datetime.datetime) -> int:
    return date.year * 100 + date.month


def get_next_period(period: int) -> int:
    return get_relative_period(period, 1)


def get_period_datetime(period: int) -> datetime.datetime:
    year: int = period // 100
    month: int = period % 100
    return datetime.datetime(year, month, 1)


def get_date_datetime(date: int) -> datetime.datetime:
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


def get_type(type_to_digest: type) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    for key, value in type_to_digest.__annotations__.items():
        if issubclass(value, Enum):
            mapping[key] = value._member_type_  # type: ignore
        else:
            mapping[key] = value
    return mapping


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


def simulate(
    data_path: str,
    start_date: int,
    end_date: int,
    new_clients_count: int,
    new_accounts_count: int,
    generator: np.random.Generator,
) -> None:
    # load clients
    clients_path: str = os.path.join(data_path, "clients.csv")
    try:
        clients_df = pd.read_csv(clients_path, dtype=get_type(ClientsRow))
    except FileNotFoundError:
        clients_df = pd.DataFrame(columns=list(ClientsRow.__annotations__.keys()))
    # load accounts
    accounts_path: str = os.path.join(data_path, "accounts.csv")
    try:
        accounts_df = pd.read_csv(accounts_path, dtype=get_type(AccountsRow))
    except FileNotFoundError:
        accounts_df = pd.DataFrame(columns=list(AccountsRow.__annotations__.keys()))
    # load transactions
    transactions_path: str = os.path.join(data_path, "transactions.csv")
    try:
        transactions_df = pd.read_csv(
            transactions_path, dtype=get_type(TransactionsRow)
        )
    except FileNotFoundError:
        transactions_df = pd.DataFrame(
            columns=list(TransactionsRow.__annotations__.keys())
        )
    # load collection actions
    collection_actions_path: str = os.path.join(data_path, "collection_actions.csv")
    try:
        collection_actions_df = pd.read_csv(
            collection_actions_path, dtype=get_type(CollectionActionsRow)
        )
    except FileNotFoundError:
        collection_actions_df = pd.DataFrame(
            columns=list(CollectionActionsRow.__annotations__.keys()),
        )
    start_date_datetime: datetime.datetime = get_date_datetime(start_date)
    end_date_datetime: datetime.datetime = get_date_datetime(end_date)
    if clients_df.empty:
        next_cid: int = 1
    else:
        next_cid: int = int(clients_df["cid"].max()) + 1
    current_date: datetime.datetime = start_date_datetime
    while current_date < end_date_datetime:
        current_period: int = get_period(current_date)
        # generate new clients
        new_clients: List[Client] = []
        for _ in range(new_clients_count):
            cid: str = str(next_cid).zfill(10)
            client: Client = Client.get_starter(
                cid, generator, 2, current_date=current_date
            )
            new_clients.append(client)
            next_cid += 1
        # add new clients to dataframe
        new_clients_df: pd.DataFrame = pd.DataFrame(
            [client.to_dict() for client in new_clients]
        )
        clients_df = pd.concat([clients_df, new_clients_df], ignore_index=True)
        # generate new accounts
        new_accounts: List[Account] = []
        new_transactions: List[TransactionsRow] = []
        for client_index, client in enumerate(new_clients):
            aid: str = generate_aid(current_date, "ins", client_index + 1)
            account: Account = Account.generate_account(
                client, aid, current_date, generator
            )
            new_accounts.append(account)
            # generate first transaction
            new_transaction: TransactionsRow = get_first_transaction_row(
                client.cid, aid, current_period
            )
            new_transactions.append(new_transaction)
        # add new accounts to dataframe
        new_clients = []
        new_accounts_df: pd.DataFrame = pd.DataFrame(
            [account.to_dict() for account in new_accounts]
        )
        accounts_df = pd.concat([accounts_df, new_accounts_df], ignore_index=True)
        new_accounts = []
        # add new transactions to dataframe
        new_transactions_df: pd.DataFrame = pd.DataFrame(
            [transaction for transaction in new_transactions]
        )
        transactions_df = pd.concat(
            [transactions_df, new_transactions_df], ignore_index=True
        )
        if is_last_day_of_month(current_date):
            production_df: pd.DataFrame = make_production_df(clients_df, accounts_df)
            abt_base_current_period: pd.DataFrame = make_abt_base(
                production_df, transactions_df, current_period
            )
            abt_base_current_period_path: str = os.path.join(
                data_path, f"abt_base_{current_period}.csv"
            )
            abt_base_current_period.to_csv(abt_base_current_period_path, index=False)
            summary_abt: pd.DataFrame = make_summary_abt(current_period)
            summary_abt_path: str = os.path.join(
                data_path, f"summary_abt_{current_period}.csv"
            )
            summary_abt.to_csv(summary_abt_path, index=False)
            # generate transactions
            new_transactions: List[TransactionsRow] = []
            # get transactions for the last period where status == A
            # transactions_current_period: pd.DataFrame = transactions_df[
            #     (transactions_df["period"] == current_period)
            #     & (transactions_df["status"] == Status.A)
            # ]
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
                summary_abt[["act_due", "score"]]
                .groupby("act_due")
                .agg({"score": "count"})
            )
            for i in range(0, 13):
                if i in stat.index:
                    counts_array[i] = stat.loc[i, "score"]

            print(counts_array)

            for act_due_group_value, act_due_group in summary_abt.sort_values(
                by=["act_due", "score"], ascending=[True, False]
            ).groupby("act_due"):
                ob: int = 0
                for _, summary_row in act_due_group.iterrows():
                    ob += 1
                    if summary_row["aid"] in last_actions:
                        last_action: str = last_actions[summary_row["aid"]]
                    else:
                        last_action: str = "0"
                    is_reaction_positive: bool = calculate_positive_reaction(
                        last_action, generator
                    )
                    appropriate_matrix = (
                        data_mat_positive if is_reaction_positive else data_mat
                    )
                    act_due: int = summary_row["act_due"]
                    act_paid: int = summary_row["act_paid_installments"]

                    new_due_installments: int = act_due
                    new_paid_installments: int = act_paid
                    new_status: Status = summary_row["status"]
                    pay_days: int = 0
                    if 0 <= act_due < 12:
                        probability: float = 0.0
                        for potential_due_installments in range(12, -1, -1):
                            probability: float = appropriate_matrix[
                                act_due, 0:potential_due_installments
                            ].sum()
                            condition: bool = ob > probability * counts_array[act_due]
                            if condition:
                                # Movement from act_due to to
                                new_due_installments = potential_due_installments
                                newly_paid_installments: int = (
                                    1 + act_due - potential_due_installments
                                )
                                new_paid_installments = (
                                    act_paid + newly_paid_installments
                                )
                                if act_due < potential_due_installments:
                                    # No payment
                                    pay_days = 0
                                else:
                                    # Payment
                                    if (
                                        new_paid_installments
                                        > summary_row["app_n_installments"]
                                    ):
                                        new_paid_installments = summary_row[
                                            "app_n_installments"
                                        ]
                                    if act_due < 2:
                                        pay_days = -int(
                                            15 * abs(generator.normal(0, 1)) / 4
                                        )
                                    else:
                                        pay_days = int(15 * generator.normal(0, 1) / 4)
                                break
                            # probability += appropriate_matrix[
                            #     act_due, potential_due_installments
                            # ]

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
                        fin_period=get_next_period(current_period),
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
            collection_actions_df = pd.concat(
                [collection_actions_df, new_collection_actions_df], ignore_index=True
            )
            # add new transactions to dataframe
            new_transactions_df: pd.DataFrame = pd.DataFrame(
                [transaction for transaction in new_transactions]
            )
            transactions_df = pd.concat(
                [transactions_df, new_transactions_df], ignore_index=True
            )
            pass
        if is_last_day_of_year(current_date):
            clients = Client.get_list_from_dataframe(clients_df)
            for client in clients:
                client.simulate_next_year(generator=generator)
            clients_df: pd.DataFrame = pd.DataFrame(
                [client.to_dict() for client in clients], columns=clients_df.columns
            )

        # Perform operations for the current period if needed
        current_date += datetime.timedelta(days=1)
    # generate new accounts

    # save clients
    clients_df.to_csv(clients_path, index=False)
    # save accounts
    accounts_df.to_csv(accounts_path, index=False)
    # save transactions
    transactions_df.to_csv(transactions_path, index=False)
    # save collection actions
    collection_actions_df.to_csv(collection_actions_path, index=False)
    # save metadata
    metadata_path: str = os.path.join(data_path, "metadata.json")
    metadata = {
        "current_date": get_date_int(current_date),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
